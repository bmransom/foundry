> **Status:** Validating (2026-06-28) — implemented, gate green (`check-fast: PASS`); the live `lldb` eval is the pending check; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — debug-skill

## Wave 1 — the skill

- T1 `plugins/foundry/skills/debug/SKILL.md` + `references/lldb.md` + `gdb-map.md`: the core
  `lldb` workflow — launch/attach, breakpoints (file:line / symbol / conditional), execution
  control, frame/variable/backtrace inspection, exit — within the ≤120-line budget;
  `name`/`description` frontmatter; the full cheatsheet and the `lldb`↔`gdb` map in `references/`,
  each linked from `SKILL.md` (AC-1.1–1.4, AC-2.1, AC-4.1).
- Gate: `scripts/check-context-budget.sh` (≤120) + `scripts/check-skill-references.sh` (every
  `references/` file reachable from `SKILL.md`) — both already in `check-fast`.

## Wave 2 — the eval + knowledge

- T2 `evals/fixtures/debug/` (a tiny C program with a seeded defect — out-of-bounds write or null
  deref — + a build command) + `evals/harness/grade_debug.py` (the grader, in `evals/harness/`
  per the `grade_*.py` precedent): the grader asserts the transcript shows a breakpoint hit, a
  frame/variable inspected, and the faulting line named (AC-3.1, AC-3.2). Live → gated/deferred.
- T3 `evals/harness/test_grade_debug.py` + `tests/grade_debug_test.sh` (the shim `check-fast`'s
  `tests/*_test.sh` glob discovers, mirroring `tests/grade_navigation_test.sh`): two canned
  transcripts — a debugger-used run passes, a static-only correct guess fails — proving the grader
  discriminates deterministically in the gate, without the live run (AC-3.3).
- T4 `plugins/foundry/skills/debug/references/walkthrough.md`: the seeded-bug session, start to
  localization; link it from `SKILL.md` (`check-skill-references.sh` requires every `references/`
  file reachable) (AC-4.1).
- T5 `knowledge/log.md`: record the skill; confirm no glossary row needed (AC-4.2).
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; `tests/grade_debug_test.sh` (→
  `test_grade_debug.py`) discriminates (a static-only transcript fails). The **live** debugger
  eval is deferred — not a gate or Done blocker; route the card through `Validating` for the live
  run if desired.
