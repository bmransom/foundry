#!/usr/bin/env bash
# The spec-convergence hook turns edit -> review into a bounded loop: it continues
# on FINDINGS, stops on CLEAN, and escalates at the cap. spec-review is stubbed so
# the loop CONTROL is tested deterministically (reviewer quality is reviewer-eval's job).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK="$REPO/plugins/foundry/scripts/spec-convergence-hook.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$HOOK" ] || fail "missing spec-convergence-hook.sh"

grep -q 'SPEC_CONVERGENCE_CAP:-10' "$HOOK" || fail "default cap should be 10"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cat > "$work/stub-review" <<'STUB'
#!/usr/bin/env bash
v="$(head -1 "$STUB_SEQ")"
tail -n +2 "$STUB_SEQ" > "$STUB_SEQ.tmp"; mv "$STUB_SEQ.tmp" "$STUB_SEQ"
if [ "$v" = "CLEAN" ]; then echo "(no findings)"; echo "SPEC_REVIEW: CLEAN"
elif [ "$v" = "DRIFT" ]; then echo "prose, but no verdict line"
else echo "FLAGGED: hedge-word in design.md"; echo "SPEC_REVIEW: FINDINGS"; fi
STUB
chmod +x "$work/stub-review"
export SPEC_CONVERGENCE_REVIEW_CMD="$work/stub-review"

run() {  # invoke the hook (it exits 2/4); capture output + rc without aborting
  set +e
  HOOK_OUT="$(bash "$HOOK" roadmap/specs/demo 2>&1)"; HOOK_RC=$?
  set -e
}

# Arm A — convergence: FINDINGS, FINDINGS, CLEAN -> loop runs twice, then stops clean.
export SPEC_CONVERGENCE_STATE="$work/stateA" STUB_SEQ="$work/seqA" SPEC_CONVERGENCE_CAP=10
printf 'FINDINGS\nFINDINGS\nCLEAN\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 2 ] || fail "A1 expected continue(2), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *"round 1/10"*FLAGGED:*) ;; *) fail "A1 output: $HOOK_OUT" ;; esac
run; [ "$HOOK_RC" -eq 2 ] || fail "A2 expected continue(2), got $HOOK_RC"
case "$HOOK_OUT" in *"round 2/10"*) ;; *) fail "A2 output: $HOOK_OUT" ;; esac
run; [ "$HOOK_RC" -eq 0 ] || fail "A3 expected converged(0), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *"CLEAN — converged"*) ;; *) fail "A3 output: $HOOK_OUT" ;; esac

# Arm B — cap: FINDINGS x3 with cap 3 -> escalate on the 3rd, never loops forever.
export SPEC_CONVERGENCE_STATE="$work/stateB" STUB_SEQ="$work/seqB" SPEC_CONVERGENCE_CAP=3
printf 'FINDINGS\nFINDINGS\nFINDINGS\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 2 ] || fail "B1 expected continue(2), got $HOOK_RC"
run; [ "$HOOK_RC" -eq 2 ] || fail "B2 expected continue(2), got $HOOK_RC"
run; [ "$HOOK_RC" -eq 4 ] || fail "B3 expected escalate(4), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *"CAP REACHED (3/3)"*escalate*) ;; *) fail "B3 output: $HOOK_OUT" ;; esac

# Arm C — verdict drift: no SPEC_REVIEW line -> hard error, not a silent pass.
export SPEC_CONVERGENCE_STATE="$work/stateC" STUB_SEQ="$work/seqC" SPEC_CONVERGENCE_CAP=10
printf 'DRIFT\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -eq 3 ] || fail "C expected drift-error(3), got $HOOK_RC: $HOOK_OUT"
case "$HOOK_OUT" in *"no 'SPEC_REVIEW"*) ;; *) fail "C output: $HOOK_OUT" ;; esac

echo "spec_convergence_hook_test: PASS"
