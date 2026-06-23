#!/usr/bin/env bash
# The spec-convergence eval must DISCRIMINATE: a loop that reports CLEAN while the
# seeded defect remains (fake-clean) must FAIL; a loop that actually removes the
# defect then reports CLEAN must PASS. The oracle is an independent grep, not the
# reviewer's own say-so.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL="$REPO/evals/harness/spec-convergence-eval.sh"
FIXTURE="$REPO/evals/fixtures/spec-convergence/design.md"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$EVAL" ] || fail "missing spec-convergence-eval.sh"
[ -f "$FIXTURE" ] || fail "missing fixture"
grep -q "SEEDED-DEFECT-HEDGE" "$FIXTURE" || fail "fixture must carry the seeded defect signature"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# fake-clean driver: claims CLEAN but never edits the spec.
cat > "$work/fake_clean" <<'D'
#!/usr/bin/env bash
echo "SPEC_REVIEW: CLEAN"
D

# real-converge driver: strips the seeded defect, then reports CLEAN.
cat > "$work/converge" <<'D'
#!/usr/bin/env bash
grep -v 'SEEDED-DEFECT-HEDGE' "$1" > "$1.tmp" && mv "$1.tmp" "$1"
echo "SPEC_REVIEW: CLEAN"
D

# never-converges driver: reports FINDINGS forever, never removes the defect.
cat > "$work/stuck" <<'D'
#!/usr/bin/env bash
echo "FLAGGED: still hedged"
echo "SPEC_REVIEW: FINDINGS"
D
chmod +x "$work/fake_clean" "$work/converge" "$work/stuck"

# fake-clean -> the eval must FAIL (catches the lie via the independent grep).
if SPEC_CONVERGENCE_DRIVER="$work/fake_clean" bash "$EVAL" >/dev/null 2>&1; then
  fail "eval passed a fake-clean loop (defect still present) — oracle is not discriminating"
fi

# never-converges -> the eval must FAIL.
if SPEC_CONVERGENCE_DRIVER="$work/stuck" bash "$EVAL" >/dev/null 2>&1; then
  fail "eval passed a non-converging loop"
fi

# real convergence -> the eval must PASS.
SPEC_CONVERGENCE_DRIVER="$work/converge" bash "$EVAL" >/dev/null 2>&1 \
  || fail "eval failed a genuinely converged spec (defect removed + CLEAN)"

echo "spec_convergence_eval_test: PASS"
