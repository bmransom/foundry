> **Status:** Draft (2026-06-25).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — lifecycle autonomy

Waves run top to bottom. Every task names the gate that proves it and the AC it satisfies.

## Wave 1 — Spec
- [ ] T1: Spec files + board card; pre-approval `spec-review` to CLEAN. Gate: review
  CLEAN, or every finding has a recorded disposition. [AC: all]

## Wave 2 — The dial (reference + skill pointer)
- [ ] T2: `references/autonomy.md` — the dial: the three levels + the soft-fork/hard-blocker
  split, the stop-point kinds, the run-state convention
  (`.foundry/tmp/lifecycle-run.json`: `level`, `stopPoint`, `completed`, `startedAt` —
  agent-managed, no script, so it works in any consumer repo without a plugin-path
  dependency), the continuation loop, the run summary, the harness integration (`/loop`,
  Codex `/goal`), and the invariant push/merge floor.
  [AC-1.2, AC-1.3, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-4.1, AC-4.2, AC-4.3]
- [ ] T3: `code/SKILL.md` — a concise Autonomy line in Frame (resolve + record the
  directive) and a continuation line after Finish (advance toward the stop-point), each
  pointing to `references/autonomy.md`; trim to stay within the 120-line context budget.
  [AC-1.1, AC-1.4]

## Wave 3 — Gate (static test)
- [ ] T4: `tests/lifecycle_autonomy_skill_test.sh` — assert `references/autonomy.md` names
  the three levels, the stop-point kinds, the soft-fork/hard-blocker split, the invariant,
  the directive precedence, the run-state path + schema, and the `/loop`+`/goal` mapping;
  and that `code/SKILL.md` points to it. Gate: the test is executable and PASSES;
  `scripts/check-fast.sh` PASS (context budget included). [all AC]

## Wave 4 — Behavioral proof + knowledge
- [ ] T5: Behavioral proof via the lifecycle-e2e dogfood — `Guided`, stop at a named card:
  the run stops at exactly that card (not past it), never pushes/merges to the default
  branch, and a soft fork is decided + recorded (Autonomous) or asked (Guided). Gate: the
  dogfood report shows the stop-point honored + the invariant held. [Metrics]
- [ ] T6: Glossary — "Autonomy level" + "Stop-point" rows with provenance and an explicit
  em-dash in the "Replaces (now debt)" column (they replace nothing); knowledge log.
  Gate: `python3 scripts/knowledge.py check` clean. [Glossary impact]

## Wave 5 — Verify
- [ ] T7: `scripts/check-fast.sh` PASS; card → Validating. Gate: pasted PASS.
