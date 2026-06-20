#!/usr/bin/env bash
# Safe-failure checks for the shared fresh-session runner: isolation failures
# stop loudly and never fall back to the shared tree.
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
trap 'for w in "$scratch"/*; do [ -d "$w/.git" ] && git -C "$w" worktree prune 2>/dev/null; done; rm -rf "$scratch"' EXIT

# A real git repo fixture.
repo="$scratch/repo"
git init -q -b main "$repo"
git -C "$repo" config user.email "foundry@example.test"
git -C "$repo" config user.name "Foundry Test"
printf '.foundry/tmp/\n' > "$repo/.gitignore"
printf '# fixture\n' > "$repo/README.md"
git -C "$repo" add .gitignore README.md
git -C "$repo" commit -qm "initial"

# --- AC-6.1: a non-git caller dir refuses unless FOUNDRY_SPAWN_ALLOW_NON_GIT=1.
nongit="$scratch/nongit"
mkdir -p "$nongit"

set +e
refuse_out="$(printf 'p\n' | TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name x "$nongit" 2>&1)"
refuse_code=$?
set -e
[ "$refuse_code" -ne 0 ] || fail "AC-6.1: must refuse to spawn in a non-git dir"
case "$refuse_out" in
  *REFUSING*|*"not a git repo"*) ;;
  *) fail "AC-6.1: refusal must name the non-git reason (got: $refuse_out)" ;;
esac
case "$refuse_out" in
  *new-window*) fail "AC-6.1: must NOT launch tmux when refusing" ;;
esac
[ ! -e "$nongit/.foundry" ] || fail "AC-6.1: must not write a prompt when refusing"

# AC-6.1: the opt-out spawns in place and warns on stderr that isolation is lost.
allow_out="$(printf 'p\n' | FOUNDRY_SPAWN_ALLOW_NON_GIT=1 TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name x "$nongit" 2>&1)"
case "$allow_out" in
  *WARNING*|*"in place"*) ;;
  *) fail "AC-6.1: the opt-out must warn that isolation is lost (got: $allow_out)" ;;
esac
launch_cwd_nongit="$(printf '%s\n' "$allow_out" | grep new-window | awk '{for (i=1;i<NF;i++) if ($i=="-c") {print $(i+1); exit}}')"
[ "$launch_cwd_nongit" = "$nongit" ] || fail "AC-6.1: the opt-out spawns in place (cwd = caller dir)"

# --- AC-6.2: git worktree unavailable exits nonzero.
# Shim a fake git on PATH that fails `git worktree --help` but answers
# rev-parse so is_git_repo still sees a repo.
shimdir="$scratch/shim"
mkdir -p "$shimdir"
real_git="$(command -v git)"
cat > "$shimdir/git" <<SHIM
#!/usr/bin/env bash
if [ "\$1" = "worktree" ]; then
  echo "git: 'worktree' is not a git command" >&2
  exit 1
fi
exec "$real_git" "\$@"
SHIM
chmod +x "$shimdir/git"

set +e
nowt_out="$(printf 'p\n' | PATH="$shimdir:$PATH" TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name x "$repo" 2>&1)"
nowt_code=$?
set -e
[ "$nowt_code" -ne 0 ] || fail "AC-6.2: must exit nonzero when git worktree is unavailable"
case "$nowt_out" in
  *new-window*) fail "AC-6.2: must NOT launch tmux when git worktree is unavailable" ;;
esac

# --- AC-6.3: a failed `git worktree add` removes the partial path and the
# just-made branch, and does not start tmux.
# Shim git so `worktree add` fails AFTER creating the branch and the path,
# mirroring a real partial failure.
addfaildir="$scratch/addfail"
mkdir -p "$addfaildir"
cat > "$addfaildir/git" <<SHIM
#!/usr/bin/env bash
# Intercept: git -C <dir> worktree add -b <branch> <path> <base>
dir=""
args=("\$@")
for ((i = 0; i < \${#args[@]}; i++)); do
  case "\${args[i]}" in
    -C) dir="\${args[i+1]}" ;;
    worktree)
      if [ "\${args[i+1]:-}" = "add" ] && [ "\${args[i+2]:-}" = "-b" ]; then
        branch="\${args[i+3]}"; path="\${args[i+4]}"
        # Partial creation: make the branch and the path, then fail — so the
        # runner's rollback must remove both.
        "$real_git" -C "\$dir" branch "\$branch" >/dev/null 2>&1 || true
        mkdir -p "\$path"
        echo "fatal: simulated worktree add failure" >&2
        exit 1
      fi
      ;;
  esac
done
exec "$real_git" "\$@"
SHIM
chmod +x "$addfaildir/git"

set +e
addfail_out="$(printf 'p\n' | PATH="$addfaildir:$PATH" TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$RUNNER" --name addfail "$repo" 2>&1)"
addfail_code=$?
set -e
[ "$addfail_code" -ne 0 ] || fail "AC-6.3: must exit nonzero when worktree add fails"
case "$addfail_out" in
  *new-window*) fail "AC-6.3: must NOT launch tmux when worktree add fails" ;;
esac
# The partial worktree path must be gone.
leftover="$(find "$repo/.foundry/tmp/fresh-session" -type d -name worktree 2>/dev/null || true)"
[ -z "$leftover" ] || fail "AC-6.3: must remove the partial worktree path (left: $leftover)"
# The just-made foundry/fs/* branch must be gone (cleaned up only after verify).
if "$real_git" -C "$repo" for-each-ref --format='%(refname:short)' 'refs/heads/foundry/fs/*' | grep -q .; then
  fail "AC-6.3: must delete the just-made foundry/fs/* branch on add failure"
fi

# --- AC-6.4: unknown harness or missing tmux still creates the worktree and
# prints `cd <worktree> && <command>`.
notmuxdir="$scratch/notmux"
mkdir -p "$notmuxdir"
# A PATH with git but no tmux: use AGENT_TMUX pointing at a nonexistent binary
# and unset TMUX so the runner takes the manual-print branch.
manual_out="$(printf 'p\n' | AGENT_HARNESS=codex AGENT_TMUX=definitely-not-a-real-tmux-binary "$RUNNER" --name manual "$repo" 2>&1)"
case "$manual_out" in
  *"cd "*"/worktree"*"&&"*"codex"*) ;;
  *) fail "AC-6.4: missing tmux must print 'cd <worktree> && <command>' (got: $manual_out)" ;;
esac
# The worktree was still created.
manual_wt="$(printf '%s\n' "$manual_out" | sed -n 's/^cd \(.*\) && .*/\1/p' | head -1)"
[ -d "$manual_wt" ] || fail "AC-6.4: must still create the worktree when tmux is missing"
case "$(git -C "$manual_wt" branch --show-current)" in
  foundry/fs/*) ;;
  *) fail "AC-6.4: the created worktree must be on a foundry/fs/<id> branch" ;;
esac

echo "fresh_session_failmode_test: PASS"
