> **Status:** In progress (2026-06-28) — spec approved; implementing on `card/review-convergence`; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — review-convergence

## Summary

Bring `spec-review`'s convergence loop to `code-review`'s bar: gate on **substance, not
taste**. spec-review findings gain a `blocking | advisory` severity; the `FLAGGED:` footer
lists blocking findings only; `SPEC_REVIEW: CLEAN` means **no unresolved blocking finding**.
The convergence re-pass of **both `spec-review` and `code-review`** is made **blind** —
context-isolated, never handed a summary of what changed (code-review shares this gap; its
DROP-only refuter cannot recover a missed finding). Objective writing-style rules move to a
**deterministic linter** so taste never enters the binary gate. A **shared cross-family
review pass** (Claude Code / Codex) — code-review uses it DROP-only (precision), spec-review
UNION (recall) — catches what one model misses. Closes
[`review-convergence-coe`](../../../knowledge/review-convergence-coe.md): a primed,
severity-blind loop passed `CLEAN` over a real contradiction.

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

- AC-3.1 THE objective writing-style rule — a defined banned-filler-phrase set — SHALL be
  enforced by a deterministic linter in the gate, not by the judge.
- AC-3.2 THE spec-review judge's prose taste findings SHALL be `advisory`.
- AC-3.3 A debt term used for its concept SHALL stay a `blocking` judge call — many debt terms
  have a legitimate non-debt use ("issue" is debt for a board row but fine as a GitHub issue),
  so a deterministic scan cannot tell a violation from legitimate use.
- AC-3.4 THE banned-filler-phrase set SHALL be generic English with no repo vocabulary, so
  the verbatim twin ships no repo-specific content (mechanisms-not-content).

## US-4 — Loop termination on no-new-blocking

- AC-4.1 THE convergence loop SHALL converge (verdict `CLEAN`) when a round leaves no
  unresolved `blocking` finding, within the existing per-spec cap.
- AC-4.2 WHEN the cap is reached with a `blocking` finding unresolved, THE loop SHALL escalate
  to the human without auto-approving (unchanged).

## US-5 — A shared cross-family review pass

A second review pass on a **different harness family** (Claude Code / Codex) catches what one
model's blind spot misses — the bias-reducing move only when the judges are decorrelated.
`code-review` already has this as a DROP-only refuter; `spec-review` needs the inverse
(its failure mode is misses, not false positives), and both should share one mechanism.

- AC-5.1 A shared mechanism SHALL spawn a context-isolated review pass on the harness family
  complementary to the reviewer's, derived from `.foundry/manifest.json` via
  `refuter-family.sh`.
- AC-5.2 WHEN no complementary family exists (single-family repo or no manifest), THE
  mechanism SHALL skip the pass and run single-agent.
- AC-5.3 THE shared mechanism SHALL be parameterized by a goal prompt; the combine-rule is a
  caller-side Strategy (a `footer-algebra` set op — UNION for spec-review, DROP for
  code-review), not a parameter of the shared mechanism.
- AC-5.4 `code-review`'s pass SHALL combine **DROP-only** — the final footer is the
  candidates minus the second family's DROPs (unchanged).
- AC-5.5 `spec-review`'s pass SHALL combine **UNION** — the second family's `blocking`
  findings are added to the first reviewer's blocking set.
- AC-5.6 THE spec-review cross-family pass SHALL ship enabled only after its eval proves it
  raises recall with no decoy-hit regression — the same A/B discipline that gates
  code-review's refuter.

## Metrics

- A seeded **blocking** contradiction holds the gate (`FINDINGS`); a seeded **prose nit**
  converges to `CLEAN` (advisory, non-blocking) — measured by the eval.
- A **primed** re-review misses a seeded contradiction that the **blind** re-pass catches.
- The loop terminates within the cap on substance — no non-convergence over taste.
- The cross-family UNION pass raises spec-review recall on a fixture where one family misses a
  `blocking` finding the other catches, with no decoy-hit regression (AC-5.6).
