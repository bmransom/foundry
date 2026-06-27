#!/usr/bin/env bash
# T25: hermetic A/B refuter-gating test. Drives code-review-eval.sh --score-ab on canned
# findings files — it NEVER spawns claude (it only scores text against the answer key).
# The refuter ships enabled ONLY if Arm B (reviewer+refuter) holds mean recall >= 4/5 AND
# zero decoy hits: Arm B holding the bar => "refuter ENABLED" (exit 0); Arm B dropping two
# real violations => "refuter DISABLED" (exit nonzero). This is the eval-gates-the-gate
# discipline (the eval decides whether the refuter is on), tested deterministically.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL="$REPO/evals/harness/code-review-eval.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$EVAL" ] || fail "missing/!executable code-review-eval.sh"
work="$(mktemp -d)"
trap 'rm -rf "$work"; rm -f "$REPO"/evals/results/code-review-*-armA.ndjson "$REPO"/evals/results/code-review-*-armB.ndjson 2>/dev/null || true' EXIT

# All 5 seeded violations, zero decoy signatures — holds the bar (recall 5/5, decoys 0).
flag_all() {
  printf 'FLAGGED: AC-2.1\nFLAGGED: sync complete\nFLAGGED: gargantuan_pricing_engine\nFLAGGED: --purge-cache\nFLAGGED: shipping job\nCODE_REVIEW: FAIL\n'
}
flag_all > "$work/armA.txt"
flag_all > "$work/armB.txt"

# Arm B holds the bar -> refuter ENABLED, exit 0.
set +e; out="$("$EVAL" --score-ab "$work/armA.txt" "$work/armB.txt" 2>&1)"; rc=$?; set -e
grep -q "refuter ENABLED" <<<"$out" || fail "Arm B holding the bar must ENABLE the refuter: $out"
[ "$rc" -eq 0 ] || fail "ENABLED must exit 0, got $rc: $out"

# Arm B drops two real violations (flags 3/5 -> recall 0.6 < 0.8) -> refuter DISABLED, nonzero.
printf 'FLAGGED: AC-2.1\nFLAGGED: sync complete\nFLAGGED: gargantuan_pricing_engine\nCODE_REVIEW: FAIL\n' > "$work/armB_weak.txt"
set +e; out="$("$EVAL" --score-ab "$work/armA.txt" "$work/armB_weak.txt" 2>&1)"; rc=$?; set -e
grep -q "refuter DISABLED" <<<"$out" || fail "Arm B below the bar must DISABLE the refuter: $out"
[ "$rc" -ne 0 ] || fail "DISABLED must exit nonzero, got 0: $out"

echo "code_review_eval_test: PASS"
