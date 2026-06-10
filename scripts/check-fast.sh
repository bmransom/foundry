#!/usr/bin/env bash
# The quick gate: lock-free; runs from .githooks/pre-push and CI.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== plugin validate"
claude plugin validate "$REPO/plugins/foundry"

echo "== byte identity"
"$REPO/scripts/check-byte-identity.sh"

echo "== script tests"
for test_file in "$REPO"/tests/*_test.sh; do
  bash "$test_file"
done

echo "check-fast: PASS"
