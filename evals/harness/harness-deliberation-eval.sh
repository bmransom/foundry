#!/usr/bin/env bash
# Deterministic eval driver for harness-deliberation fixtures.
set -euo pipefail

usage() {
  echo "usage: harness-deliberation-eval.sh [--seed-defect <case>] [repo-root]" >&2
}

seed_defect=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --seed-defect)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      seed_defect="$2"
      shift 2
      ;;
    -*) echo "harness-deliberation-eval: unknown argument '$1'" >&2; usage; exit 2 ;;
    *) break ;;
  esac
done

REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
FIXTURES="$REPO/evals/fixtures/harness-deliberation/cases.json"

[ -f "$FIXTURES" ] || { echo "harness-deliberation-eval: missing fixtures" >&2; exit 1; }

if [ -n "$seed_defect" ]; then
  if ! grep -q "\"$seed_defect\"" "$FIXTURES"; then
    echo "harness-deliberation-eval: unknown seeded defect: $seed_defect" >&2
    exit 2
  fi
  echo "seeded defect caught: $seed_defect" >&2
  exit 1
fi

tests=(
  tests/harness_status_test.sh
  tests/harness_deliberation_broker_test.sh
  tests/harness_deliberation_start_test.sh
  tests/harness_deliberation_round_test.sh
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
