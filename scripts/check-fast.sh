#!/usr/bin/env bash
# Foundry-local gate checks, run as the `[gate].commands` entry inside `foundry gate`
# (config.toml). The board, prose, and knowledge checks are NOT here — the gate suite
# (foundry.gate.board/prose/knowledge) runs them natively before this script.
set -euo pipefail

# Git's pre-push hook exports GIT_DIR/GIT_WORK_TREE/etc. into this gate; left
# set, they hijack the `git init` and `git commit` the eval and isolation tests
# run on their own fixture repos, committing into THIS repo instead. Clear them
# so a gate run can never mutate the real repo.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_PREFIX \
      GIT_CONFIG_PARAMETERS GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== plugin validate"
claude plugin validate "$REPO/plugins/foundry"
claude plugin validate "$REPO"

echo "== manifest parity"
"$REPO/scripts/check-manifest-parity.sh"

echo "== byte identity"
"$REPO/scripts/check-byte-identity.sh"

echo "== gate tools"
"$REPO/scripts/check-gate-tools.sh"

echo "== context budget"
"$REPO/scripts/check-context-budget.sh"

echo "== skill references"
"$REPO/scripts/check-skill-references.sh"

echo "== knowledge tool tests"
(cd "$REPO" && python3 scripts/test_knowledge.py)

echo "== script tests"
test_files=("$REPO"/tests/*_test.sh)
[ -e "${test_files[0]}" ] || { echo "check-fast: no test files found in tests/" >&2; exit 1; }
for test_file in "${test_files[@]}"; do
  bash "$test_file"
done

echo "== pytest"
(cd "$REPO" && uv run pytest -q)

echo "check-fast: PASS"
