#!/usr/bin/env bash
# Handoff inheritance: a handoff spawned from a LINKED worktree reuses it (no
# new foundry/fs/* branch, parent WIP preserved); a handoff from the PRIMARY
# tree promotes once to a new worktree.
#
# Hermetic: AGENT_TMUX=/bin/echo, TMUX=1. No real claude/codex/tmux required.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO/plugins/foundry/scripts/spawn-fresh-session.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -x "$RUNNER" ] || fail "missing executable shared fresh-session runner"

scratch="$(mktemp -d)"
repo="$scratch/repo"
trap '
  for w in "$repo"/.foundry/tmp/fresh-session/*/worktree "$scratch"/parent-wt; do
    [ -d "$w" ] && git -C "$repo" worktree remove --force "$w" 2>/dev/null || true
  done
  git -C "$repo" worktree prune 2>/dev/null || true
  rm -rf "$scratch"
' EXIT

git init -q -b main "$repo"
git -C "$repo" config user.email "foundry@example.test"
git -C "$repo" config user.name "Foundry Test"
printf '.foundry/tmp/\n' > "$repo/.gitignore"
printf '# fixture\n' > "$repo/README.md"
git -C "$repo" add .gitignore README.md
git -C "$repo" commit -qm "initial"

extract_cwd() {
  awk '{for (i = 1; i < NF; i++) if ($i == "-c") { print $(i + 1); exit }}'
}
branch_count() {
  git -C "$repo" for-each-ref --format='%(refname:short)' 'refs/heads/foundry/fs/*' | grep -c . || true
}

# --- AC-2.2: a handoff from the PRIMARY tree promotes to a new worktree.
before_primary="$(branch_count)"
primary_out="$(printf 'resume\n' | TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name primary-handoff "$repo")"
after_primary="$(branch_count)"
[ "$after_primary" -eq "$((before_primary + 1))" ] || fail "AC-2.2: a primary-tree handoff must promote to a new foundry/fs/* worktree"
primary_cwd="$(printf '%s\n' "$primary_out" | grep new-window | extract_cwd)"
case "$primary_cwd" in
  "$repo"/.foundry/tmp/fresh-session/*/worktree) ;;
  *) fail "AC-2.2: primary-tree handoff must launch in the new worktree (got $primary_cwd)" ;;
esac

# --- AC-2.1 / AC-2.3: a handoff from a LINKED worktree reuses it.
# Create a linked worktree by hand, leave uncommitted WIP in it, then spawn a
# handoff with the linked worktree as the caller dir.
parent_wt="$scratch/parent-wt"
git -C "$repo" worktree add -q -b some/parent-work "$parent_wt" HEAD
printf 'work in progress\n' > "$parent_wt/WIP.txt"     # untracked WIP
printf '# edited\n' >> "$parent_wt/README.md"          # uncommitted tracked edit

before_linked="$(branch_count)"
linked_out="$(printf 'resume\n' | TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name linked-handoff "$parent_wt")"
after_linked="$(branch_count)"

# AC-2.1: no new foundry/fs/* branch minted.
[ "$after_linked" -eq "$before_linked" ] || fail "AC-2.1: a handoff in a linked worktree must NOT mint a new foundry/fs/* branch"

# AC-2.1: the launch cwd is the parent worktree itself, not a new one.
linked_cwd="$(printf '%s\n' "$linked_out" | grep new-window | extract_cwd)"
[ "$linked_cwd" = "$parent_wt" ] || fail "AC-2.1: a linked-worktree handoff must reuse the parent worktree (got $linked_cwd)"

# AC-2.3: the parent's uncommitted WIP is preserved.
[ -f "$parent_wt/WIP.txt" ] || fail "AC-2.3: untracked WIP must be preserved"
grep -q "work in progress" "$parent_wt/WIP.txt" || fail "AC-2.3: untracked WIP content must be preserved"
grep -q "# edited" "$parent_wt/README.md" || fail "AC-2.3: uncommitted tracked edit must be preserved"

echo "fresh_session_handoff_inherit_test: PASS"
