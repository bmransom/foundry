#!/usr/bin/env bash
# Guardrail checks: the runner sets a per-session GIT_CONFIG_GLOBAL inside the
# session dir, documents that worktrees share .git/config, and installs no PATH
# git shim.
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
  for w in "$repo"/.foundry/tmp/fresh-session/*/worktree; do
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

out="$(printf 'work\n' | TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name guard "$repo")"

# AC-3.1: the launch sets GIT_CONFIG_GLOBAL to a file inside the session dir.
launch="$(printf '%s\n' "$out" | grep new-window || true)"
cfg="$(printf '%s\n' "$launch" | grep -oE 'GIT_CONFIG_GLOBAL=[^ ]+' | head -1 | cut -d= -f2- || true)"
[ -n "$cfg" ] || fail "AC-3.1: launch must set GIT_CONFIG_GLOBAL"
case "$cfg" in
  "$repo"/.foundry/tmp/fresh-session/*/gitconfig) ;;
  *) fail "AC-3.1: GIT_CONFIG_GLOBAL must point inside the session dir (got $cfg)" ;;
esac
[ -f "$cfg" ] || fail "AC-3.1: the per-session gitconfig file must be created"

# The per-session config lives in the PRIMARY tree, not inside the worktree.
wt="$(printf '%s\n' "$launch" | awk '{for (i=1;i<NF;i++) if ($i=="-c") {print $(i+1); exit}}')"
case "$cfg" in
  "$wt"/*) fail "AC-3.1: the per-session gitconfig must live in the primary tree, not the worktree" ;;
esac

# AC-3.2: the runner documents that worktrees share .git/config.
grep -qi "worktrees share .git/config\|SHARE .git/config" "$RUNNER" \
  || fail "AC-3.2: the runner must document that worktrees share .git/config"

# AC-3.3: no PATH git shim is installed — the runner never writes an executable
# named 'git' nor prepends a shim dir to PATH.
if grep -qE 'PATH=.*shim|cat > .*/git\b|/git" <<|export PATH=' "$RUNNER"; then
  fail "AC-3.3: the runner must NOT install a PATH git shim"
fi
# No 'git' file was dropped anywhere under the session dir.
if find "$repo/.foundry/tmp/fresh-session" -name git -type f 2>/dev/null | grep -q .; then
  fail "AC-3.3: no git shim file may be created"
fi

echo "fresh_session_gitconfig_guard_test: PASS"
