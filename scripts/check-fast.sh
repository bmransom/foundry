#!/usr/bin/env bash
# The quick gate: lock-free; runs from .githooks/pre-push and CI.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== plugin validate"
claude plugin validate "$REPO/plugins/foundry"
claude plugin validate "$REPO"

echo "== byte identity"
"$REPO/scripts/check-byte-identity.sh"

echo "== script tests"
test_files=("$REPO"/tests/*_test.sh)
[ -e "${test_files[0]}" ] || { echo "check-fast: no test files found in tests/" >&2; exit 1; }
for test_file in "${test_files[@]}"; do
  bash "$test_file"
done

echo "check-fast: PASS"
