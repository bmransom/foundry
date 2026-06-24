#!/usr/bin/env bash
# The code-review convergence hook turns review -> fix -> re-review into a bounded
# OUTER loop: continue on FAIL, converge on PASS, escalate at the cap. The reviewer
# is stubbed via the test-only seam so the loop CONTROL is tested deterministically
# (reviewer quality is the code-review eval's job). Mirrors spec_convergence_hook_test.sh.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO/plugins/foundry/scripts/code-review-convergence-hook.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$HOOK" ] || fail "missing code-review-convergence-hook.sh"

grep -q 'CODE_REVIEW_CONVERGENCE_CAP:-20' "$HOOK" || fail "default cap should be 20"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cat > "$work/stub-review" <<'STUB'
#!/usr/bin/env bash
v="$(head -1 "$STUB_SEQ")"
tail -n +2 "$STUB_SEQ" > "$STUB_SEQ.tmp"; mv "$STUB_SEQ.tmp" "$STUB_SEQ"
if [ "$v" = "PASS" ]; then echo "(no blocking findings)"; echo "CODE_REVIEW: PASS"
elif [ "$v" = "DRIFT" ]; then echo "prose, but no verdict line"
else echo "FLAGGED: bug in foo.py:10"; echo "CODE_REVIEW: FAIL"; fi
STUB
chmod +x "$work/stub-review"
export CODE_REVIEW_REVIEW_CMD="$work/stub-review"

run() {  # invoke the hook (exits 0/2/4); capture output + rc without aborting
  set +e
  HOOK_OUT="$(bash "$HOOK" roadmap/specs/demo 2>&1)"; HOOK_RC=$?
  set -e
}

# Arm A — converge: FAIL, FAIL, PASS -> continue twice (exit 2), then converge (exit 0).
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateA" STUB_SEQ="$work/seqA" CODE_REVIEW_CONVERGENCE_CAP=20
printf 'FAIL\nFAIL\nPASS\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 2 ] || fail "A1 expected continue(2), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *"round 1/20"*FLAGGED:*) ;; *) fail "A1 output: $HOOK_OUT" ;; esac
run; [ "$HOOK_RC" -eq 2 ] || fail "A2 expected continue(2), got $HOOK_RC"
case "$HOOK_OUT" in *"round 2/20"*) ;; *) fail "A2 output: $HOOK_OUT" ;; esac
run; [ "$HOOK_RC" -eq 0 ] || fail "A3 expected converged(0), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *PASS*|*converged*) ;; *) fail "A3 output: $HOOK_OUT" ;; esac

# Arm B — immediate PASS -> converge on round 1.
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateB" STUB_SEQ="$work/seqB" CODE_REVIEW_CONVERGENCE_CAP=20
printf 'PASS\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 0 ] || fail "B expected converged(0), got $HOOK_RC: $HOOK_OUT"

# Arm C — escalate at the cap: FAIL x3 with cap 3 -> continue, continue, escalate(4).
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateC" STUB_SEQ="$work/seqC" CODE_REVIEW_CONVERGENCE_CAP=3
printf 'FAIL\nFAIL\nFAIL\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 2 ] || fail "C1 expected continue(2), got $HOOK_RC"
run; [ "$HOOK_RC" -eq 2 ] || fail "C2 expected continue(2), got $HOOK_RC"
run; [ "$HOOK_RC" -eq 4 ] || fail "C3 expected escalate(4) at cap, got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *CAP*|*escalat*) ;; *) fail "C3 output: $HOOK_OUT" ;; esac

# Arm D — reviewer drift (no verdict line) errors, never silently passes.
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateD" STUB_SEQ="$work/seqD" CODE_REVIEW_CONVERGENCE_CAP=20
printf 'DRIFT\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -ne 0 ] || fail "D expected nonzero on reviewer drift, got 0: $HOOK_OUT"

echo "code_review_cycle_test: PASS"
