> **Status:** Planned (2026-06-29) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — verify-by-execution

## Wave 1 — the executor mechanism

- T1 `plugins/foundry/scripts/verify-finding.sh`: given a finding (claim, `file:line`, suggested
  check) + language/target, select an executor (test / snippet / native) and run it via a
  `VERIFY_EXEC_CMD` seam (default real); return `verified | refuted | unrunnable`. An unrunnable
  target degrades to `unrunnable`, never errors (AC-2.1, AC-3.2, AC-4.2).
- T2 Native executor: when the target is buildable native, route to the `debug` skill (build with
  symbols, breakpoint at the claimed site, reproduce) — reproduce → verified, else refuted; folds
  `refuter-reproduce` (AC-4.1, AC-4.2).
- Gate: `tests/verify_finding_test.sh` (mock `VERIFY_EXEC_CMD`) — reproduce→verified, not→refuted,
  unrunnable→hypothesis (AC-1.1, AC-5.1).

## Wave 2 — wire into the refuter + verdict

- T3 `plugins/foundry/skills/code-review/SKILL.md` + `references/dimensions.md`: the refuter section
  gains the rule — per **blocking, checkable** finding, run an executor; verified may block, refuted
  drops, hypothesis (un-run) is advisory; advisory nits and non-executable judgment findings are not
  run (AC-1.2, AC-1.4, AC-3.1). DROP-only preserved: execution drops or demotes, never adds
  (AC-2.2). Single-harness skips the whole path — today's read-based blocking, no demotion (AC-2.3,
  AC-1.5). Keep `SKILL.md` ≤120.
- T4 `plugins/foundry/skills/code-review/references/convergence.md`: **when execution is active**,
  the verdict blocks only on a **verified** (or mechanically-checked) blocking finding; an un-runnable
  executable blocking finding is demoted to advisory and does not fail the verdict (AC-1.3). When
  execution is off (single-harness), the verdict is unchanged from today (AC-1.5).
- Gate: `code_review_eval_test` + `verify_finding_test` pass; the existing refuter A/B test unchanged.

## Wave 3 — knowledge + board

- T5 `knowledge/glossary.md`: add `Verified finding`, `Hypothesis finding`, `Executor` with
  provenance; `knowledge/log.md` records it. Mark the `refuter-reproduce` card **Superseded →
  verify-by-execution** (folded as the native executor). Confirm the live `lldb`/test run is a
  deferred `Validating` check, not a gate blocker.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; `knowledge.py check` clean.
