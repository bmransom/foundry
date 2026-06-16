#!/usr/bin/env bash
# Shim: run static checks for bootstrap expectation JSON files inside the fast gate.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/../evals/harness/test_bootstrap_expectations.py" 2>&1
echo "bootstrap_expectations_test: PASS"
