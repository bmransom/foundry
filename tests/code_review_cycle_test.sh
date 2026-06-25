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
elif [ "$v" = "TIMEOUT" ]; then exit 1   # the review command failed / timed out
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

# Arm E — the review command fails / times out -> hook fails, NEVER converges (no false PASS).
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateE" STUB_SEQ="$work/seqE" CODE_REVIEW_CONVERGENCE_CAP=20
printf 'TIMEOUT\n' > "$STUB_SEQ"
run; [ "$HOOK_RC" -ne 0 ] || fail "E expected nonzero on a failed/timed-out review, got 0: $HOOK_OUT"

# ============================================================================
# Synchronous runner arms (T19): drive the REAL spawn-code-reviewer.sh through the
# spawn seam. The seam stubs the detached reviewer/refuter spawn with a script that
# writes the canned artifact, so the runner's wait -> read -> compute-verdict ->
# refuter-recompute orchestration runs deterministically (no tmux/LLM).
# ============================================================================
RUNNER="$REPO/plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh"
repo="$work/repo"; mkdir -p "$repo"
cat > "$work/stub-spawn" <<'STUB'
#!/usr/bin/env bash
# args: <role> <output-path> — write the canned artifact for that role (or nothing).
role="$1"; out="$2"
case "$role" in
  reviewer)
    spec="${STUB_REVIEWER:-none}"
    case "$spec" in
      SEQ:*) seq="${spec#SEQ:}"; f="$(head -1 "$seq" 2>/dev/null || true)"
             tail -n +2 "$seq" > "$seq.t" 2>/dev/null || true; mv "$seq.t" "$seq" 2>/dev/null || true
             [ "${f:-none}" = "none" ] || cp "$f" "$out" ;;
      none) ;;
      *) cp "$spec" "$out" ;;
    esac ;;
  refuter)  [ "${STUB_REFUTER:-none}"  = "none" ] || cp "$STUB_REFUTER"  "$out" ;;
esac
STUB
chmod +x "$work/stub-spawn"

run_runner() {  # $1 reviewer-family $2 refuter-family|none $3 reviewer(file|none|SEQ:path) $4 refuter $5 timeout $6 extra-flag $7 review-cap
  rm -rf "$repo/.foundry/reports"   # no leftover report from a same-second prior arm
  local extra=(); [ -n "${6:-}" ] && extra=("$6")
  # $2 forces the refuter family via --harness (the manifest-derived path); "none" = single-agent.
  [ "${2:-none}" != "none" ] && extra=("--harness" "$2" ${extra[@]+"${extra[@]}"})
  set +e
  RUN_OUT="$(CODE_REVIEW_SPAWN_CMD="$work/stub-spawn" \
    CODE_REVIEW_REVIEWER_FAMILY="$1" \
    STUB_REVIEWER="$3" STUB_REFUTER="$4" \
    CODE_REVIEW_WAIT_TIMEOUT="$5" CODE_REVIEW_WAIT_POLL=0.1 CODE_REVIEW_REVIEW_CAP="${7:-20}" \
    bash "$RUNNER" ${extra[@]+"${extra[@]}"} --base BASEREF roadmap/specs/demo "$repo" 2>&1)"
  RUN_RC=$?
  set -e
}
verdict_of() { grep -E '^CODE_REVIEW:' <<<"$1" | tail -1; }

# Arm F — verdict COMPUTED from the FLAGGED footer, not the reviewer's forged line.
printf 'body\nFLAGGED: AC-2.1\nCODE_REVIEW: PASS\n' > "$work/rep-F"   # forged PASS
run_runner claude "none" "$work/rep-F" none 3
[ "$RUN_RC" -eq 0 ] || fail "F runner should succeed, rc=$RUN_RC: $RUN_OUT"
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: FAIL" ] || fail "F must COMPUTE FAIL from the footer, not trust the forged PASS: $RUN_OUT"
grep -q '^FLAGGED: AC-2.1' <<<"$RUN_OUT" || fail "F must surface the flagged finding"

# Arm G — no findings + forged FAIL -> computed PASS.
printf 'all clean\nCODE_REVIEW: FAIL\n' > "$work/rep-G"   # forged FAIL
run_runner claude "none" "$work/rep-G" none 3
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: PASS" ] || fail "G must COMPUTE PASS (no FLAGGED), not trust the forged FAIL: $RUN_OUT"

# Arm H — refuter DROP recomputes the footer + verdict (two families).
printf 'body\nFLAGGED: AC-2.1\nFLAGGED: db.py:7\nCODE_REVIEW: FAIL\n' > "$work/rep-H"
printf 'DROP AC-2.1\nKEEP db.py:7\nREFUTER: DONE\n' > "$work/ref-H"
run_runner claude "codex" "$work/rep-H" "$work/ref-H" 3
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: FAIL" ] || fail "H survivors -> FAIL: $RUN_OUT"
grep -q '^FLAGGED: db.py:7' <<<"$RUN_OUT" || fail "H kept finding must survive: $RUN_OUT"
grep -q 'AC-2.1' <<<"$RUN_OUT" && fail "H dropped finding must be gone: $RUN_OUT"

# Arm H2 — refuter DROPs every finding -> PASS.
printf 'DROP AC-2.1\nDROP db.py:7\nREFUTER: DONE\n' > "$work/ref-H2"
run_runner claude "codex" "$work/rep-H" "$work/ref-H2" 3
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: PASS" ] || fail "H2 all dropped -> PASS: $RUN_OUT"

# Arm I — reviewer never writes -> timeout -> FAIL (nonzero), never PASS.
run_runner claude "none" none none 1
[ "$RUN_RC" -ne 0 ] || fail "I timeout must fail (nonzero), rc=0: $RUN_OUT"
grep -q 'CODE_REVIEW: PASS' <<<"$RUN_OUT" && fail "I timeout must never emit PASS: $RUN_OUT"

# Arm J — inner loop UNIONS findings across passes and converges (2 consecutive no-new).
# seq: {A}, {A,B}(new), {A,B}, {A,B} -> converges at pass 4. A 5th pass would exhaust the
# seq (none -> timeout), so success proves bounded convergence by the union, not the cap.
printf 'FLAGGED: A\nCODE_REVIEW: FAIL\n' > "$work/p1"
printf 'FLAGGED: A\nFLAGGED: B\nCODE_REVIEW: FAIL\n' > "$work/p2"; cp "$work/p2" "$work/p3"; cp "$work/p2" "$work/p4"
printf '%s\n' "$work/p1" "$work/p2" "$work/p3" "$work/p4" > "$work/seqJ"
run_runner claude "none" "SEQ:$work/seqJ" none 3
[ "$RUN_RC" -eq 0 ] || fail "J inner loop should converge, rc=$RUN_RC: $RUN_OUT"
grep -q '^FLAGGED: A' <<<"$RUN_OUT" || fail "J union must keep A: $RUN_OUT"
grep -q '^FLAGGED: B' <<<"$RUN_OUT" || fail "J union must add B from a later pass: $RUN_OUT"
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: FAIL" ] || fail "J survivors -> FAIL"

# Arm K — --single-pass does EXACTLY ONE pass (seq has one entry; a 2nd pass would time out).
printf 'FLAGGED: A\nCODE_REVIEW: FAIL\n' > "$work/k1"; printf '%s\n' "$work/k1" > "$work/seqK"
run_runner claude "none" "SEQ:$work/seqK" none 2 --single-pass
[ "$RUN_RC" -eq 0 ] || fail "K --single-pass should do one pass and succeed, rc=$RUN_RC: $RUN_OUT"
[ "$(verdict_of "$RUN_OUT")" = "CODE_REVIEW: FAIL" ] || fail "K single pass -> FAIL from {A}: $RUN_OUT"

# Arm L — the inner loop stops at the CAP when findings never stop growing.
# cap=3 with a 3-entry growing seq; a 4th pass would exhaust the seq, so success proves the ceiling.
printf 'FLAGGED: A\nCODE_REVIEW: FAIL\n' > "$work/l1"
printf 'FLAGGED: A\nFLAGGED: B\nCODE_REVIEW: FAIL\n' > "$work/l2"
printf 'FLAGGED: A\nFLAGGED: B\nFLAGGED: C\nCODE_REVIEW: FAIL\n' > "$work/l3"
printf '%s\n' "$work/l1" "$work/l2" "$work/l3" > "$work/seqL"
run_runner claude "none" "SEQ:$work/seqL" none 3 "" 3
[ "$RUN_RC" -eq 0 ] || fail "L should stop at the cap, rc=$RUN_RC: $RUN_OUT"
grep -q '^FLAGGED: C' <<<"$RUN_OUT" || fail "L must union through the capped passes (C present): $RUN_OUT"

# Arm M — --fix-cap flag caps the OUTER loop (flag path, distinct from the env seam).
export CODE_REVIEW_CONVERGENCE_STATE="$work/stateM" STUB_SEQ="$work/seqM"
unset CODE_REVIEW_CONVERGENCE_CAP   # the flag, not the env, must set the cap
printf 'FAIL\nFAIL\nFAIL\n' > "$work/seqM"
set +e
bash "$HOOK" --fix-cap 3 roadmap/specs/demo >/dev/null 2>&1; m1=$?
bash "$HOOK" --fix-cap 3 roadmap/specs/demo >/dev/null 2>&1; m2=$?
mout="$(bash "$HOOK" --fix-cap 3 roadmap/specs/demo 2>&1)"; m3=$?
set -e
{ [ "$m1" -eq 2 ] && [ "$m2" -eq 2 ] && [ "$m3" -eq 4 ]; } || fail "M --fix-cap 3 must escalate at round 3, got $m1/$m2/$m3: $mout"

# Runner cap flags are accepted (parsed) — a dry-run with both exits 0.
TMUX=1 CODE_REVIEW_REVIEWER_FAMILY=claude AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
  bash "$RUNNER" --dry-run --review-cap 5 --consecutive-clean 1 --base X roadmap/specs/demo "$repo" >/dev/null 2>&1 \
  || fail "runner must accept --review-cap and --consecutive-clean"

echo "code_review_cycle_test: PASS"
