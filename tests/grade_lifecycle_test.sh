#!/usr/bin/env bash
# Shim: run the lifecycle-eval grader's python unit tests inside the fast gate
# (tests/*_test.sh is the gate's discovery glob; the grader lives in evals/).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_grade_lifecycle.py" 2>&1
echo "grade_lifecycle_test: PASS"
