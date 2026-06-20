#!/usr/bin/env bash
# Isolation checks for the shared fresh-session runner: every spawn runs in its
# own git worktree on its own foundry/fs/<id> branch, never the source tree.
#
# Hermetic: AGENT_TMUX=/bin/echo captures the launch command; TMUX=1 selects the
# new-window path. No real claude/codex/tmux binary is required.
#
# Discrimination: the seeded-defect arm runs a mutant runner that writes the
# prompt and launches in the SOURCE dir (the pre-fix behavior). The same
# assertions must FAIL against it — green-ness alone is not the evaluator.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO/plugins/foundry/scripts/spawn-fresh-session.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -x "$RUNNER" ] || fail "missing executable shared fresh-session runner"

# A real git fixture: the runner must create worktrees against it.
fixture="$(mktemp -d)"
trap 'git -C "$fixture" worktree prune 2>/dev/null || true; rm -rf "$fixture"' EXIT
git -C "$fixture" init -q -b main
git -C "$fixture" config user.email "foundry@example.test"
git -C "$fixture" config user.name "Foundry Test"
printf '.foundry/tmp/\n' > "$fixture/.gitignore"
printf '# fixture\n' > "$fixture/README.md"
git -C "$fixture" add .gitignore README.md
git -C "$fixture" commit -qm "initial"

# spawn <runner> <slug> -> echoes the captured launch line on stdout.
spawn() {
  local runner="$1" slug="$2"
  printf 'Do the work in %s\n' "$slug" |
    TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo \
      "$runner" --name "$slug" "$fixture"
}

# extract_cwd <launch-line> -> the value passed to tmux -c.
extract_cwd() {
  awk '{for (i = 1; i < NF; i++) if ($i == "-c") { print $(i + 1); exit }}'
}

# --- Assertions, factored so the mutant arm reuses them. -------------------

assert_isolation() {
  local runner="$1"
  local out_a out_b cwd_a cwd_b

  local before_branch before_status
  before_branch="$(git -C "$fixture" branch --show-current)"
  before_status="$(git -C "$fixture" status --short)"

  out_a="$(spawn "$runner" iso-a)"
  out_b="$(spawn "$runner" iso-b)"

  cwd_a="$(printf '%s\n' "$out_a" | grep new-window | extract_cwd)"
  cwd_b="$(printf '%s\n' "$out_b" | grep new-window | extract_cwd)"

  # AC-1.4: the launch cwd is the worktree, not the source dir.
  case "$cwd_a" in
    "$fixture"/.foundry/tmp/fresh-session/*/worktree) ;;
    *) return 1 ;;
  esac
  case "$cwd_b" in
    "$fixture"/.foundry/tmp/fresh-session/*/worktree) ;;
    *) return 1 ;;
  esac

  # AC-1.5: two spawns get distinct worktree paths.
  [ "$cwd_a" != "$cwd_b" ] || return 1

  # AC-1.1 / AC-1.5: each worktree is a real checkout on a distinct
  # foundry/fs/<id> branch.
  [ -d "$cwd_a" ] || return 1
  [ -d "$cwd_b" ] || return 1
  local branch_a branch_b
  branch_a="$(git -C "$cwd_a" branch --show-current)"
  branch_b="$(git -C "$cwd_b" branch --show-current)"
  case "$branch_a" in foundry/fs/*) ;; *) return 1 ;; esac
  case "$branch_b" in foundry/fs/*) ;; *) return 1 ;; esac
  [ "$branch_a" != "$branch_b" ] || return 1

  # AC-1.6: the source tree's branch and status are unchanged.
  [ "$(git -C "$fixture" branch --show-current)" = "$before_branch" ] || return 1
  [ "$(git -C "$fixture" status --short)" = "$before_status" ] || return 1

  return 0
}

assert_isolation "$RUNNER" || fail "isolated runner must spawn distinct worktrees on foundry/fs/* branches with the worktree as launch cwd and an unchanged source tree"

# --- Seeded defect: a mutant runner that launches in the SOURCE dir. -------
# It copies the real runner but rewrites the prompt dir to the source tree and
# never creates a worktree, so it launches with -c <source>. The same
# assertions MUST fail against it, proving the test discriminates.

mutant="$(mktemp -d)/spawn-mutant.sh"
mkdir -p "$(dirname "$mutant")"
# shellcheck disable=SC2016
cat > "$mutant" <<'MUTANT'
#!/usr/bin/env bash
# Pre-fix behavior: write the prompt under the source dir and launch tmux with
# -c <source dir>. No worktree, no branch.
set -euo pipefail
slug="fresh-session"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --name) slug="$2"; shift 2 ;;
    -*) shift ;;
    *) break ;;
  esac
done
dir="${1:-$PWD}"
prompt="$(cat)"
session_id="$(date +%Y%m%d%H%M%S)-$slug-$$"
prompt_dir=".foundry/tmp/fresh-session/$session_id"
mkdir -p "$dir/$prompt_dir"
printf '%s\n' "$prompt" > "$dir/$prompt_dir/prompt.md"
read -r -a tmux_bin <<< "${AGENT_TMUX:-tmux}"
"${tmux_bin[@]}" new-window -d -n "$slug" -c "$dir" "claude 'Read $prompt_dir/prompt.md'"
MUTANT
chmod +x "$mutant"

if assert_isolation "$mutant"; then
  fail "seeded-defect mutant runner (launches in source dir) must FAIL the isolation assertions"
fi

echo "fresh_session_worktree_test: PASS"
