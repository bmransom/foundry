> **Status:** Planned (2026-06-27) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — review-convergence

## Wave 1 — severity-gated spec-review contract

- T1 `plugins/foundry/skills/spec-review/SKILL.md`: Output contract — each finding carries
  `blocking`/`advisory`; `FLAGGED:` carries the blocking findings; `SPEC_REVIEW: CLEAN` = no
  unresolved blocking. Update the "Flag" section to class contract violations blocking, taste
  advisory (AC-1.1–1.6).
- T2 `plugins/foundry/skills/spec-review/SKILL.md` **and
  `plugins/foundry/skills/code-review/SKILL.md`** Fresh-context workflow: the re-pass is
  **blind** — forbid handing the reviewer a change summary, and replace any "review inline"
  escape hatch with holding the gate when fresh context is unavailable (AC-2.1, 2.2, 2.3).
- Gate: `plugin_skills_test` + `context-budget` green; the contract reads coherently.

## Wave 2 — the loop honors severity

- T3 `plugins/foundry/scripts/spec-convergence-hook.sh`: confirm the stop token converges on
  `CLEAN` = no blocking and still escalates at the cap; add a hook test asserting a report
  whose only findings are advisory yields `CLEAN`/exit 0, and a blocking finding yields the
  next round/exit 2 (AC-4.1, 4.2).
- Gate: the new hook test + `spec_convergence_hook_test` pass.

## Wave 3 — objective prose to a deterministic linter

- T4 `scripts/prose-lint.py` (+ `test_prose_lint.py`, verbatim twins): a defined needless-word
  set + debt terms **derived at runtime from the consumer's `knowledge/glossary.md`** (only the
  mechanism in the twin, never a term list — AC-3.3); wire into `check-fast.sh`.
  Discrimination: a seeded debt term / needless word fails, clean prose passes (AC-3.1).
- T5 `plugins/foundry/skills/spec-review/SKILL.md`: state that the judge's prose findings are
  advisory; the linter owns objective rules (AC-3.2).
- Gate: `python3 scripts/test_prose_lint.py` passes; byte-identity twins green.

## Wave 4 — eval + knowledge

- T6 `evals/harness/spec-convergence-eval.sh` + `evals/fixtures/spec-convergence`: **migrate
  the seeded hedge defect** (`SEEDED-DEFECT-HEDGE` / `SPEC_CONVERGENCE_SIGNATURE`) to a
  **blocking** contract violation so `CLEAN` still requires its removal (else a now-advisory
  hedge trips the fake-clean branch); then add the blocking-holds, nit-converges, and
  primed-vs-blind discrimination cases (Metrics).
- T7 `evals/fixtures/reviewer/answer-key.json`: reassign **V8** (needless-qualifier) to
  `prose-lint`'s discrimination set; demote **V7** (passive/buried-point) and **V9**
  (prose-should-be-table) to advisory and drop them from the scored recall set — subjective
  judge calls with no deterministic home. The reviewer-eval recall set then keeps only blocking
  contract-violations, so recall does not regress under the blocking-only footer (AC-1.2, 3.2).
  Re-run `reviewer-eval` and record the recovered recall.
- T8 `knowledge/log.md`: log the convergence change (no `glossary.md` row — keep code-review's
  recorded "no spec-review glossary row" decision). Close
  `knowledge/review-convergence-coe.md` (Status → closed) once the eval lands.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; each seeded eval defect fails the gate.
