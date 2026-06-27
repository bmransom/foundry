#!/usr/bin/env bash
# Tracer bullet (T31): the footer-set algebra — union, dedup, difference — keyed on ONE
# normalized signature. The convergence loop's correctness rests on that key: it must
# dedup true duplicates (case/whitespace variants) yet NEVER collide near-duplicates
# (AC-2.1 vs AC-2.10), and must handle file:line and multi-word signatures. Hermetic.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
A="$REPO/plugins/foundry/skills/code-review/scripts/footer-algebra.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$A" ] || fail "missing/!executable footer-algebra.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# union: dedup true duplicates, preserve first-seen order, NO near-dup collision.
# p2's first line is a case/whitespace variant of p1's AC-2.1 -> must dedup to one.
printf 'FLAGGED: AC-2.1\nFLAGGED: report.py:42 oversized\nFLAGGED: AC-2.10\n' > "$work/p1"
printf 'FLAGGED:   ac-2.1\nFLAGGED: db.py:7 raw print\n' > "$work/p2"
u="$("$A" union "$work/p1" "$work/p2")"
[ "$(grep -c '^FLAGGED:' <<<"$u")" -eq 4 ] || fail "union: expected 4 distinct findings, got: $u"
grep -q 'AC-2.1$' <<<"$u" || fail "union: AC-2.1 must survive"
grep -q 'AC-2.10$' <<<"$u" || fail "union: AC-2.10 must survive (no collision with AC-2.1)"
[ "$(grep -ci 'ac-2\.1$' <<<"$u")" -eq 1 ] || fail "union: AC-2.1 must appear once (case/whitespace dedup): $u"

# difference: drop by normalized key; a DROP of AC-2.10 must NOT take AC-2.1.
printf 'findings...\nFLAGGED: AC-2.1\nFLAGGED: AC-2.10\nFLAGGED: report.py:42 oversized\n' > "$work/rep"
printf 'DROP ac-2.10\n' > "$work/ref"
d="$("$A" difference "$work/rep" "$work/ref")"
grep -qx 'FLAGGED: AC-2.1' <<<"$d" || fail "difference: AC-2.1 must survive a DROP of AC-2.10"
grep -q 'AC-2.10' <<<"$d" && fail "difference: AC-2.10 should be dropped"
grep -qx 'FLAGGED: report.py:42 oversized' <<<"$d" || fail "difference: untouched finding should survive"
[ "$(tail -1 <<<"$d")" = "CODE_REVIEW: FAIL" ] || fail "difference: survivors -> FAIL"

# difference: drop everything -> PASS, no FLAGGED.
printf 'DROP ac-2.1\nDROP ac-2.10\nDROP report.py:42 oversized\n' > "$work/ref2"
d2="$("$A" difference "$work/rep" "$work/ref2")"
grep -q '^FLAGGED:' <<<"$d2" && fail "difference: all dropped -> no FLAGGED"
[ "$(tail -1 <<<"$d2")" = "CODE_REVIEW: PASS" ] || fail "difference: none left -> PASS"

echo "code_review_footer_algebra_test: PASS"
