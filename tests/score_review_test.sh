#!/usr/bin/env bash
# Shim: run the reviewer-eval scorer's python unit tests inside the fast gate
# (tests/*_test.sh is the gate's discovery glob; the scorer lives in evals/).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_score_review.py" 2>&1
echo "score_review_test: PASS"
