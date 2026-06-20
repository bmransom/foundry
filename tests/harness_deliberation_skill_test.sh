#!/usr/bin/env bash
# Static checks for the harness-deliberation skill wrapper.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$REPO/plugins/foundry/skills/harness-deliberation/SKILL.md"
RUNNER="$REPO/plugins/foundry/skills/harness-deliberation/scripts/spawn-deliberation.sh"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

frontmatter_value() {
  local key="$1" file="$2"
  awk -v key="$key" '
    NR == 1 && $0 != "---" { exit }
    NR > 1 && $0 == "---" { exit }
    NR > 1 && index($0, key ":") == 1 {
      sub("^[^:]+:[[:space:]]*", "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$file"
}

[ -f "$SKILL" ] || fail "missing $SKILL"
[ -x "$RUNNER" ] || fail "missing executable runner"
[ -x "$BROKER" ] || fail "broker must be executable"
[ "$(frontmatter_value name "$SKILL")" = "harness-deliberation" ] \
  || fail "skill name must match directory"
case "$(frontmatter_value description "$SKILL")" in
  "Use when"*) ;;
  *) fail "skill description must start with 'Use when'" ;;
esac

for command in "start --prompt" "round" "decide --file" "rebuild" "spec --out" "live-smoke"; do
  grep -q "$command" "$SKILL" \
    || fail "skill must document v1 command: $command"
done
grep -q "harness-deliberation-broker.py" "$SKILL" \
  || fail "skill must delegate to the broker"
grep -q "scripts/spawn-deliberation.sh" "$SKILL" \
  || fail "skill must expose the runner"
! grep -Eq "apply|promote|web UI|compression|--participants" "$SKILL" \
  || fail "skill must not expose deferred v1 features"

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT
printf 'prompt\n' > "$fixture/prompt.md"
dry_run="$("$RUNNER" --dry-run --prompt "$fixture/prompt.md" --session demo "$fixture")"
case "$dry_run" in
  *"harness-deliberation-broker.py start"*"--prompt $fixture/prompt.md"*"--session demo"*"--repo $fixture"*) ;;
  *) fail "runner dry-run must delegate start to the broker" ;;
esac

echo "harness_deliberation_skill_test: PASS"
