> **Status:** Planned (2026-06-27) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — review-convergence

## Summary

Bring `spec-review`'s convergence loop to `code-review`'s bar: gate on **substance, not
taste**. spec-review findings gain a `blocking | advisory` severity; the `FLAGGED:` footer
lists blocking findings only; `SPEC_REVIEW: CLEAN` means **no unresolved blocking finding**.
The convergence re-pass of **both `spec-review` and `code-review`** is made **blind** —
context-isolated, never handed a summary of what changed (code-review shares this gap; its
DROP-only refuter cannot recover a missed finding). Objective writing-style rules move to a
**deterministic linter** so taste never enters the binary gate. Closes [`review-convergence-coe`](../../../knowledge/review-convergence-coe.md):
a primed, severity-blind loop passed `CLEAN` over a real contradiction.

## Glossary impact

- **Blocking finding** / **Advisory finding** — a finding that must be resolved before the
  gate passes vs. one that may remain. Already in use by `code-review`; this extends the same
  vocabulary to spec-review. Prior art: Conventional Comments `(blocking)`/`(non-blocking)`
  decorations and Google's `Nit:` prefix (advisory-by-default). No new canonical name.

## US-1 — Severity-gated spec-review verdict

- AC-1.1 EACH spec-review finding SHALL carry a severity — `blocking` or `advisory`.
- AC-1.2 THE `FLAGGED:` footer SHALL list the `blocking` findings, one per line.
- AC-1.3 WHEN no unresolved `blocking` finding remains, THE verdict SHALL be
  `SPEC_REVIEW: CLEAN`.
- AC-1.4 WHEN an unresolved `blocking` finding remains, THE verdict SHALL be
  `SPEC_REVIEW: FINDINGS`.
- AC-1.5 A contract violation (naming, glossary, spec-format, or internal-consistency) SHALL
  be classed `blocking`.
- AC-1.6 A taste-level prose preference SHALL be classed `advisory`.

## US-2 — Blind re-review (both review skills)

Applies to the convergence re-pass of **both `spec-review` and `code-review`** — code-review
shares this gap: its re-review is blind only by the scripted runner, not by contract, and its
cross-model refuter is DROP-only (precision), so it cannot recover a blocking finding a primed
re-review *missed*.

- AC-2.1 THE convergence re-pass of `spec-review` and `code-review` SHALL review the artifact
  in context isolation.
- AC-2.2 THE re-pass SHALL NOT be given a summary of what changed between rounds — the
  reviewer sees the artifact and the contract, never the author's account of the edits.
- AC-2.3 WHEN fresh context is unavailable, THE skill SHALL NOT substitute a primed inline
  re-review — it holds the gate and says so, rather than letting the author's account stand in
  for an independent pass.

## US-3 — Objective prose to a deterministic linter

- AC-3.1 THE objective writing-style rules — banned debt terms and a defined needless-word
  set — SHALL be enforced by a deterministic linter in the gate, not by the judge.
- AC-3.2 THE spec-review judge's prose findings SHALL be `advisory` — subjective taste is not
  a gate.
- AC-3.3 THE linter SHALL derive any repo-specific term list (e.g. debt terms) at runtime
  from the consumer's `knowledge/glossary.md` (so the verbatim twin carries only the
  mechanism — see design).

## US-4 — Loop termination on no-new-blocking

- AC-4.1 THE convergence loop SHALL converge (verdict `CLEAN`) when a round leaves no
  unresolved `blocking` finding, within the existing per-spec cap.
- AC-4.2 WHEN the cap is reached with a `blocking` finding unresolved, THE loop SHALL escalate
  to the human without auto-approving (unchanged).

## Metrics

- A seeded **blocking** contradiction holds the gate (`FINDINGS`); a seeded **prose nit**
  converges to `CLEAN` (advisory, non-blocking) — measured by the eval.
- A **primed** re-review misses a seeded contradiction that the **blind** re-pass catches.
- The loop terminates within the cap on substance — no non-convergence over taste.
