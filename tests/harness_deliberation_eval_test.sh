#!/usr/bin/env bash
# Static and runtime checks for the harness-deliberation eval driver.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL="$REPO/evals/harness/harness-deliberation-eval.sh"
FIXTURES="$REPO/evals/fixtures/harness-deliberation"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -x "$EVAL" ] || fail "missing executable eval driver"
[ -f "$FIXTURES/cases.json" ] || fail "missing fixture case manifest"

for case_name in replay payload snapshot truncation protocol spec stall fake-participant availability-result; do
  grep -q "\"$case_name\"" "$FIXTURES/cases.json" \
    || fail "fixture manifest missing $case_name"
done

clean_output="$("$EVAL" "$REPO")"
case "$clean_output" in
  *"harness-deliberation-eval: PASS"*) ;;
  *) fail "clean eval must pass" ;;
esac

# The non-discriminating --seed-defect grep is retired; discrimination now lives
# in the standalone tests (command-surface, mediator-prompt render, resume).
if "$EVAL" --seed-defect payload "$REPO" >/dev/null 2>&1; then
  fail "the retired --seed-defect flag must no longer be accepted"
fi

echo "harness_deliberation_eval_test: PASS"
