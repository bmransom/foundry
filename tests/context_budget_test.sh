#!/usr/bin/env bash
# Tests for scripts/check-context-budget.sh against a fixture tree.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../scripts/check-context-budget.sh"
FIXTURE_ROOT="$(mktemp -d)"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

make_fixture() {
  fixture="$(mktemp -d "$FIXTURE_ROOT/case.XXXXXX")"
  mkdir -p "$fixture/plugins/foundry/skills/code"
  mkdir -p "$fixture/plugins/foundry/agents"
  mkdir -p "$fixture/plugins/foundry/templates/seeds/.claude/rules"
  # 10-line skill — well under budget
  printf '%s\n' {1..10} > "$fixture/plugins/foundry/skills/code/SKILL.md"
  # 10-line agent — well under budget
  printf '%s\n' {1..10} > "$fixture/plugins/foundry/agents/spec-reviewer.md"
  # 10-line seed rule — well under budget
  printf '%s\n' {1..10} > "$fixture/plugins/foundry/templates/seeds/.claude/rules/spec-conventions.md"
  echo "$fixture"
}

fail() { echo "FAIL: $1"; exit 1; }

# Case (a): all files within budget → PASS exit 0
fixture="$(make_fixture)"
"$SCRIPT" "$fixture" >/dev/null || fail "files within budget should pass"

# Case (b): skill SKILL.md over budget → fail, names file and budget
fixture="$(make_fixture)"
printf '%s\n' {1..130} > "$fixture/plugins/foundry/skills/code/SKILL.md"
output="$("$SCRIPT" "$fixture" 2>&1 || true)"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "oversize skill should fail"; fi
echo "$output" | grep -q "plugins/foundry/skills/code/SKILL.md" \
  || fail "violation output must name the file (got: $output)"
echo "$output" | grep -q "120" \
  || fail "violation output must name the budget (got: $output)"

# Case (c): agent file over budget → fail
fixture="$(make_fixture)"
printf '%s\n' {1..70} > "$fixture/plugins/foundry/agents/spec-reviewer.md"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "oversize agent should fail"; fi

# Case (d): seed rule over budget → fail
fixture="$(make_fixture)"
printf '%s\n' {1..70} > "$fixture/plugins/foundry/templates/seeds/.claude/rules/spec-conventions.md"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "oversize seed rule should fail"; fi

# Case (e): missing dirs → PASS (nothing to lint is fine)
fixture="$(mktemp -d "$FIXTURE_ROOT/case.XXXXXX")"
"$SCRIPT" "$fixture" >/dev/null || fail "missing plugin dirs should pass"

echo "context_budget_test: PASS"
