#!/usr/bin/env bash
# Shim: run the navigation-eval grader's python unit tests inside the fast gate
# (tests/*_test.sh is the gate's discovery glob; the grader lives in evals/).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_grade_navigation.py" 2>&1
echo "grade_navigation_test: PASS"
