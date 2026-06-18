#!/usr/bin/env bash
# Dry-run and prompt-file checks for the shared fresh-session runner.
set -euo pipefail

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

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT

run_output="$(
  printf 'Review target.md and write report.md\n' |
    TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo \
      "$RUNNER" --name spec-review "$fixture"
)"

case "$run_output" in
  *"new-window"*spec-review*codex*".foundry/tmp/fresh-session/"*"prompt.md"*) ;;
  *) fail "shared runner must launch codex with a short prompt-file instruction" ;;
esac

prompt_file="$(find "$fixture/.foundry/tmp/fresh-session" -name prompt.md -print -quit)"
[ -f "$prompt_file" ] || fail "shared runner must write prompt.md"
grep -q "Review target.md" "$prompt_file" \
  || fail "prompt.md must contain the original workflow prompt"

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
