# Convergence — the code-review loops

Two bounded loops drive a review to a stable verdict. The reviewer is read-only and
never fixes; the lifecycle agent fixes between outer rounds.

## Inner loop — review-convergence (one converged review)

`spawn-code-reviewer.sh` runs this; it is the default (`--single-pass` does one pass).

1. Review the diff in fresh context; write the report — findings body, `FLAGGED:`
   footer (blocking findings only), then the verdict line.
2. **Union** the pass's footer into the running set, keyed on ONE normalized signature
   (lowercase + collapsed whitespace), so `AC-2.1` and `AC-2.10` never collide.
3. Stop at **two consecutive passes that add nothing new**, or the **20-pass ceiling**.
4. Run the **cross-model refuter ONCE** over the converged union (footer + diff only).
5. **Recompute** the final footer (union minus the refuter's DROPs) and the verdict —
   FAIL iff a blocking finding survives — never the reviewer's forgeable verdict line.

A reviewer report that never completes (timeout) FAILS — never a false PASS.

## Outer loop — fix-convergence

`code-review-convergence-hook.sh` runs this as the lifecycle Review stage
(Verify → Knowledge → Review → Finish). Each invocation runs one converged inner review:

- **PASS** → converged; Review clears, Finish may proceed (exit 0).
- **FAIL** → surface the `FLAGGED:` items; the agent fixes via the SDLC (a docs or
  knowledge gap loops back to Knowledge first), which re-invokes the hook — the next
  round (exit 2).
- **20 rounds** without convergence → stop and escalate to the maintainer; never
  auto-pass (exit 4).
- No verdict, or a failed/timed-out review → not converged (exit 3).

A per-spec round counter caps non-convergence so the loop cannot run forever.

## Why these shapes

The refuter is a single asymmetric DROP-only pass (precision-up, recall-monotone-down),
run once on the union — not per pass, not a debate. The 20 caps are escalation
backstops, not steady states: hitting one signals reviewer nondeterminism or an
unsatisfiable finding that a human should see.
