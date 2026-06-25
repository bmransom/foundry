#!/usr/bin/env bash
# Deterministic slice of the lifecycle-e2e dogfood. The full eval is Layer-4/manual
# (it drives headless agents), but its INSTALL foundation is deterministic and worth
# gating: --plan renders; --setup-only creates a fresh git repo with foundry's verbatim
# templates installed byte-identical; and the byte-identity check DISCRIMINATES — a
# tampered or missing template fails --verify-only. The headless lifecycle drive is the
# heavy manual part, not exercised here.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER="$REPO/evals/harness/lifecycle-e2e-eval.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$DRIVER" ] || fail "missing/!executable lifecycle-e2e-eval.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# --plan renders the staged flow.
"$DRIVER" --plan >/dev/null || fail "--plan should exit 0"

# --setup-only: fresh repo + verbatim install + byte-identity PASS.
out="$(LIFECYCLE_E2E_SETUP_DIR="$work/repo" "$DRIVER" --setup-only)" || fail "--setup-only should succeed: $out"
grep -q "BYTE-IDENTITY PASS" <<<"$out" || fail "--setup-only must report byte-identity PASS: $out"
[ -d "$work/repo/.git" ] || fail "fresh_repo must create a git repo"

# a known verbatim file is installed byte-identical (modulo the version marker).
T="$REPO/plugins/foundry/templates/verbatim/scripts/knowledge.py"
C="$work/repo/scripts/knowledge.py"
[ -f "$C" ] || fail "install_foundry must copy scripts/knowledge.py"
diff <(grep -vF 'foundry-template:' "$T") <(grep -vF 'foundry-template:' "$C") >/dev/null \
  || fail "installed scripts/knowledge.py must match the template byte-for-byte"

# DISCRIMINATION: a drifted verbatim file must FAIL --verify-only.
echo "# tampered" >> "$work/repo/scripts/board.sh"
if LIFECYCLE_E2E_SETUP_DIR="$work/repo" "$DRIVER" --verify-only >/dev/null 2>&1; then
  fail "byte-identity must catch a drifted verbatim file"
fi

# DISCRIMINATION: a missing verbatim file must FAIL --verify-only.
rm -f "$work/repo/scripts/knowledge.py"
if LIFECYCLE_E2E_SETUP_DIR="$work/repo" "$DRIVER" --verify-only >/dev/null 2>&1; then
  fail "byte-identity must catch a missing verbatim file"
fi

echo "lifecycle_e2e_test: PASS"
