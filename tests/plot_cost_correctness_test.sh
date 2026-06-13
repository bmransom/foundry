#!/usr/bin/env bash
# Shim: run the correctness-vs-cost plotter's python unit tests inside the fast
# gate (tests/*_test.sh is the gate's discovery glob; the plotter lives in evals/).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_plot_cost_correctness.py" 2>&1
echo "plot_cost_correctness_test: PASS"
