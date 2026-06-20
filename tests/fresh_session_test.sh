#!/usr/bin/env bash
# Dry-run, prompt-file, and isolation checks for the shared fresh-session runner.
#
# Hermetic: AGENT_TMUX=/bin/echo captures the launch command; TMUX=1 selects the
# new-window path. No real claude/codex/pi/tmux binary is required.
set -euo pipefail

# Hermetic against the git-hook environment: a hook exports GIT_DIR/GIT_WORK_TREE
# etc., which would hijack `git init` of the fixture repos below. Clear them.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_PREFIX \
      GIT_CONFIG_PARAMETERS GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO/plugins/foundry/scripts/spawn-fresh-session.sh"
SPEC="$REPO/plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh"
HANDOFF="$REPO/plugins/foundry/skills/handoff/scripts/spawn-successor.sh"
EXTRACT="$REPO/plugins/foundry/skills/extract-skill/scripts/spawn-extractor.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -x "$RUNNER" ] || fail "missing executable shared fresh-session runner"
[ "$(AGENT_HARNESS=pi "$RUNNER" --print-harness)" = "pi" ] \
  || fail "shared runner must detect AGENT_HARNESS=pi"

for wrapper in "$SPEC" "$HANDOFF" "$EXTRACT"; do
  grep -q "spawn-fresh-session.sh" "$wrapper" \
    || fail "$wrapper must delegate to the shared fresh-session runner"
done

# A real git fixture: isolation creates worktrees against it.
fixture="$(mktemp -d)"
trap 'git -C "$fixture" worktree prune 2>/dev/null || true; rm -rf "$fixture"' EXIT
git -C "$fixture" init -q -b main
git -C "$fixture" config user.email "foundry@example.test"
git -C "$fixture" config user.name "Foundry Test"
printf '.foundry/tmp/\n' > "$fixture/.gitignore"
printf '# fixture\n' > "$fixture/README.md"
git -C "$fixture" add .gitignore README.md
git -C "$fixture" commit -qm "initial"

# extract_cwd <launch-line> -> the value passed to tmux -c.
extract_cwd() {
  awk '{for (i = 1; i < NF; i++) if ($i == "-c") { print $(i + 1); exit }}'
}

run_output="$(
  printf 'Review target.md and write report.md\n' |
    TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo \
      "$RUNNER" --name spec-review "$fixture"
)"

case "$run_output" in
  *"new-window"*spec-review*codex*".foundry/tmp/fresh-session/"*"prompt.md"*) ;;
  *) fail "shared runner must launch codex with a short prompt-file instruction" ;;
esac

# Isolation: the launch cwd is the per-session worktree, not the source dir.
launch_cwd="$(printf '%s\n' "$run_output" | grep new-window | extract_cwd)"
case "$launch_cwd" in
  "$fixture"/.foundry/tmp/fresh-session/*/worktree) ;;
  *) fail "launch cwd must be the per-session worktree, not the source dir (got '$launch_cwd')" ;;
esac
[ -d "$launch_cwd" ] || fail "the launch cwd worktree must exist"
case "$(git -C "$launch_cwd" branch --show-current)" in
  foundry/fs/*) ;;
  *) fail "the worktree must be checked out on a foundry/fs/<id> branch" ;;
esac

# The prompt lives under the PRIMARY session dir, passed by absolute path.
prompt_file="$(find "$fixture/.foundry/tmp/fresh-session" -name prompt.md -print -quit)"
[ -f "$prompt_file" ] || fail "shared runner must write prompt.md under the primary session dir"
case "$prompt_file" in
  "$launch_cwd"/*) fail "prompt.md must live in the primary tree, not inside the worktree" ;;
esac
grep -q "Review target.md" "$prompt_file" \
  || fail "prompt.md must contain the original workflow prompt"
printf '%s\n' "$run_output" | grep -q "$prompt_file" \
  || fail "the launch must reference the prompt by absolute primary-tree path"

spec_output="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SPEC" roadmap/specs/example/design.md "$fixture"
)"
case "$spec_output" in
  *"new-window"*spec-review*claude*".foundry/tmp/fresh-session/"*"prompt.md"*".foundry/reports/spec-review/"*) ;;
  *) fail "spec-review wrapper must use shared runner prompt file and report path" ;;
esac
grep -R "roadmap/specs/example/design.md" "$fixture/.foundry/tmp/fresh-session" >/dev/null \
  || fail "spec-review prompt file must include the target path"

handoff_output="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$HANDOFF" --dry-run next-task "$fixture"
)"
case "$handoff_output" in
  *"new-window"*next-task*claude*".foundry/tmp/fresh-session/"*"prompt.md"*) ;;
  *) fail "handoff wrapper must use shared runner" ;;
esac

mkdir -p "$fixture/.agent/skill-extractions/demo"
printf 'brief\n' > "$fixture/.agent/skill-extractions/demo/brief.md"
extract_output="$(
  TMUX=1 AGENT_HARNESS=pi AGENT_TMUX=/bin/echo \
    "$EXTRACT" --dry-run demo "$fixture/.agent/skill-extractions/demo/brief.md" "$fixture"
)"
case "$extract_output" in
  *"new-window"*extract-demo*pi*".foundry/tmp/fresh-session/"*"prompt.md"*) ;;
  *) fail "extract-skill wrapper must use shared runner" ;;
esac

grep -q "^\\.foundry/tmp/$" "$REPO/.gitignore" \
  || fail ".gitignore must ignore generated fresh-session prompts"

echo "fresh_session_test: PASS"
