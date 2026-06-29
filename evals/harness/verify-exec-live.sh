#!/usr/bin/env bash
# Live eval — verify-by-execution drives a REAL lldb session to reproduce-or-drop a native
# runtime fault. Needs lldb + cc, so it is NOT in the fast gate (run on demand, like the
# debug skill's live path). It proves the native executor end to end: the seeded heap
# out-of-bounds write reproduces (verified); the fixed target does not (refuted) — the
# proof-by-reproduction the refuter relies on, not a mock.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
V="$REPO/plugins/foundry/scripts/verify-finding.sh"
FIX="$REPO/evals/fixtures/debug"
fail() { echo "FAIL: $1" >&2; exit 1; }
command -v lldb >/dev/null && command -v cc >/dev/null \
  || { echo "verify-exec-live: SKIP (no lldb/cc on this host)"; exit 0; }
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# An lldb-driven repro check: run the ASan+symbols binary UNDER lldb in batch; the fault
# reproduces iff AddressSanitizer's heap-buffer-overflow fires inside the session.
repro_check() { echo "lldb --batch -o run -o quit $1 2>&1 | grep -q heap-buffer-overflow"; }

# Buggy target: the seeded off-by-one (i <= n) writes buf[n] -> the OOB reproduces -> verified.
cc -g -O1 -fno-inline -fsanitize=address "$FIX/buggy.c" -o "$work/buggy"
v="$("$V" run native "$work/buggy" "$(repro_check "$work/buggy")")"
[ "$v" = verified ] || fail "buggy target must be VERIFIED (lldb reproduces the OOB), got '$v'"
echo "  buggy.c -> $v (lldb reproduced the heap-buffer-overflow)"

# Fixed target: i < n -> no OOB -> does not reproduce -> refuted (the finding drops).
sed 's/i <= n/i < n/' "$FIX/buggy.c" > "$work/fixed.c"
cc -g -O1 -fno-inline -fsanitize=address "$work/fixed.c" -o "$work/fixed"
r="$("$V" run native "$work/fixed" "$(repro_check "$work/fixed")")"
[ "$r" = refuted ] || fail "fixed target must be REFUTED (no OOB to reproduce), got '$r'"
echo "  fixed.c -> $r (lldb ran clean, nothing to reproduce)"

echo "verify-exec-live: PASS — reproduce-or-drop proven via a real lldb session"
