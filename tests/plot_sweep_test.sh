#!/usr/bin/env bash
# Shim: run the sweep plotter's python unit tests inside the fast gate
# (tests/*_test.sh is the gate's discovery glob; the plotter lives in evals/).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_plot_sweep.py" 2>&1
echo "plot_sweep_test: PASS"
