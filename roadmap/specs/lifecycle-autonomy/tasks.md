> **Status:** Draft (2026-06-25).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — lifecycle autonomy

Waves run top to bottom. Every task names the gate that proves it and the AC it satisfies.

## Wave 1 — Spec
- [ ] T1: Spec files + board card; pre-approval `spec-review` to CLEAN. Gate: review
  CLEAN, or every finding has a recorded disposition. [AC: all]

## Wave 2 — Run-state
- [ ] T2: Run-state helper — read/write `.foundry/tmp/lifecycle-run.json` (level,
  stopPoint, completed). Gate: a `tests/` case round-trips the directive and defaults to
  Supervised / this-feature when absent. [AC-1.2, AC-1.3, AC-1.4]

## Wave 3 — The dial in the code skill (prose)
- [ ] T3: `code/SKILL.md` Frame stage — the Autonomy sub-step: detect a directive
  (run-state → prompt → ask), the level table, the stop-point kinds, the invariant
  push/merge boundary. Gate: a behavioral test asserts the skill text names the three
  levels, the stop-point kinds, the invariant, and the directive precedence.
  [AC-1.1, AC-1.4, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-3.1]
- [ ] T4: `code/SKILL.md` continuation loop after Finish — advance to the next card
  until the stop-point/blocker; emit the run summary. Gate: the test asserts the loop,
  the summary contract, and the per-level handback. [AC-3.2, AC-3.3, AC-3.4]
- [ ] T5: `code/SKILL.md` harness integration — `/loop`, `/goal`, interactive; the
  re-ask prohibition + the re-arm signal. Gate: the test asserts the harness mapping.
  [AC-4.1, AC-4.2, AC-4.3]

## Wave 4 — Eval + knowledge
- [ ] T6: Behavioral eval — a fixture asserting the dial discriminates: Supervised stops
  after one feature; Guided continues to the stop-point; a seeded hard blocker halts; no
  push/merge to the default branch. Gate: the eval fails if any of these holds wrong.
  [Metrics]
- [ ] T7: Glossary — "Autonomy level" + "Stop-point" rows with provenance and an explicit
  em-dash in the "Replaces (now debt)" column (they replace nothing); knowledge log.
  Gate: `python3 scripts/knowledge.py check` clean. [Glossary impact]

## Wave 5 — Verify
- [ ] T8: `scripts/check-fast.sh` PASS; card → Validating. Gate: pasted PASS.
