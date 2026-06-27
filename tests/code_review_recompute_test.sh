#!/usr/bin/env bash
# recompute-footer.sh rebuilds the final FLAGGED footer + verdict from the
# reviewer's report and the cross-model refuter's KEEP/DROP output. DROP-only: it
# can remove a reviewer finding, never add one. Verdict: FAIL iff a FLAGGED line
# survives (the footer lists blocking findings only), else PASS. This is the logic
# the wrapper previously faked with a hardcoded echo (CR-1).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
H="$REPO/plugins/foundry/skills/code-review/scripts/recompute-footer.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$H" ] || fail "missing/!executable recompute-footer.sh"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# Case 1 — DROP one of several: survivors keep order, verdict stays FAIL.
cat > "$work/r1" <<'R'
findings body...
FLAGGED: AC-2.1
FLAGGED: report.py:huge_fn
FLAGGED: sync.py:36 shipping job
CODE_REVIEW: FAIL
R
cat > "$work/f1" <<'F'
KEEP AC-2.1
DROP report.py:huge_fn
KEEP sync.py:36 shipping job
F
out="$("$H" "$work/r1" "$work/f1")"
grep -qx "FLAGGED: AC-2.1" <<<"$out" || fail "1: AC-2.1 should survive"
grep -qx "FLAGGED: sync.py:36 shipping job" <<<"$out" || fail "1: shipping job should survive"
grep -q "report.py:huge_fn" <<<"$out" && fail "1: report.py:huge_fn should be dropped"
[ "$(tail -1 <<<"$out")" = "CODE_REVIEW: FAIL" ] || fail "1: verdict should be FAIL (got: $(tail -1 <<<"$out"))"

# Case 2 — DROP the only finding: verdict flips to PASS.
printf 'body\nFLAGGED: AC-2.1\nCODE_REVIEW: FAIL\n' > "$work/r2"
printf 'DROP AC-2.1\n' > "$work/f2"
out="$("$H" "$work/r2" "$work/f2")"
grep -q "FLAGGED:" <<<"$out" && fail "2: no FLAGGED should survive"
[ "$(tail -1 <<<"$out")" = "CODE_REVIEW: PASS" ] || fail "2: verdict should be PASS"

# Case 3 — no refuter file: footer + FAIL unchanged.
printf 'body\nFLAGGED: AC-2.1\nFLAGGED: x\nCODE_REVIEW: FAIL\n' > "$work/r3"
out="$("$H" "$work/r3")"
grep -qx "FLAGGED: AC-2.1" <<<"$out" && grep -qx "FLAGGED: x" <<<"$out" || fail "3: both findings should survive"
[ "$(tail -1 <<<"$out")" = "CODE_REVIEW: FAIL" ] || fail "3: verdict should be FAIL"

# Case 4 — no FLAGGED at all: PASS.
printf 'all clean\nCODE_REVIEW: PASS\n' > "$work/r4"
out="$("$H" "$work/r4")"
[ "$(tail -1 <<<"$out")" = "CODE_REVIEW: PASS" ] || fail "4: verdict should be PASS"

# Case 5 — refuter cannot ADD: a DROP of an absent signature / a KEEP changes nothing.
printf 'body\nFLAGGED: AC-2.1\nCODE_REVIEW: FAIL\n' > "$work/r5"
printf 'DROP not-present\nKEEP AC-2.1\nDROP also-absent\n' > "$work/f5"
out="$("$H" "$work/r5" "$work/f5")"
grep -qx "FLAGGED: AC-2.1" <<<"$out" || fail "5: AC-2.1 should survive (refuter cannot add/remove-absent)"
[ "$(tail -1 <<<"$out")" = "CODE_REVIEW: FAIL" ] || fail "5: verdict should be FAIL"

echo "code_review_recompute_test: PASS"
