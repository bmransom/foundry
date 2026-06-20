#!/usr/bin/env bash
# Deterministic eval driver for harness-deliberation: runs the discriminating
# unit tests and confirms the fixture manifest is present. Each listed test
# carries its own seeded-defect assertion; this driver aggregates them.
set -euo pipefail

REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
FIXTURES="$REPO/evals/fixtures/harness-deliberation/cases.json"

[ -f "$FIXTURES" ] || { echo "harness-deliberation-eval: missing fixtures" >&2; exit 1; }

tests=(
  tests/harness_status_test.sh
  tests/harness_deliberation_broker_test.sh
  tests/harness_deliberation_start_test.sh
  tests/harness_deliberation_round_test.sh
  tests/harness_deliberation_resume_test.sh
  tests/harness_deliberation_command_surface_test.sh
  tests/harness_deliberation_decide_test.sh
  tests/harness_deliberation_stall_test.sh
  tests/harness_deliberation_worktree_test.sh
  tests/harness_deliberation_snapshot_test.sh
  tests/harness_deliberation_truncation_test.sh
  tests/harness_deliberation_spec_test.sh
  tests/harness_deliberation_spec_generation_test.sh
)

for test_file in "${tests[@]}"; do
  bash "$REPO/$test_file" >/dev/null
done

echo "harness-deliberation-eval: PASS"
