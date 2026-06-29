> **Status:** Validating (2026-06-29) — implemented, gate green (`check-fast: PASS`); the live `lldb` eval is the pending check; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — debug-skill

## Summary

A `debug` skill that teaches an agent to drive **`lldb`** to debug native code (C/C++/Rust/Swift)
— set breakpoints, control execution (run/continue/step/next/finish), inspect frames, variables,
and backtraces, and attach to a live process or load a core. Like Foundry's other skills, it is a
`SKILL.md` the agent follows while driving `lldb` through the shell — harness-agnostic. `gdb` is a
documented sibling (the same workflow, a different command surface), not a second skill.

## Glossary impact

- No new canonical name. `lldb`/`gdb` command vocabulary (breakpoint, frame, step, backtrace) is
  standard; prior art is the LLDB/GDB documentation. The skill name `debug` is descriptive — no
  glossary row; recorded in `knowledge/log.md`.

## US-1 — The skill teaches the core lldb workflow

- AC-1.1 `plugins/foundry/skills/debug/SKILL.md` SHALL cover: launch (`lldb <bin>` → `run`) and
  attach (`lldb -p <pid>`, load a core); breakpoints (file:line, symbol, conditional, list,
  delete); execution control (`continue`/`step`/`next`/`finish`); inspection (`bt`,
  `frame select`, `frame variable`/`print`, registers/memory); and exit.
- AC-1.2 THE skill SHALL be invocable — `name` + `description` frontmatter.
- AC-1.3 THE skill SHALL stay within the skill context budget (≤120 lines) — the full command
  cheatsheet lives in `references/`.
- AC-1.4 THE skill SHALL drive `lldb` through the shell (`Bash`), with no harness-specific
  command — so it works under any harness that loads skills.

## US-2 — gdb as a sibling, not a duplicate skill

- AC-2.1 THE skill SHALL note `gdb` as a sibling via an `lldb`↔`gdb` command map in `references/`,
  NOT as a separate skill — the workflow is identical; only the command surface differs.

## US-3 — It guides a real debugging session (the eval)

- AC-3.1 AN eval SHALL seed a tiny native program with a known defect (e.g. an out-of-bounds
  write or null dereference) and assert a skill-guided agent **localizes the faulting line via
  `lldb`** — sets a breakpoint, steps, and inspects the offending frame/variable.
- AC-3.2 Discrimination: the eval SHALL assert the debugger was actually used (a breakpoint hit
  and a frame/variable inspected in the transcript), not a correct static guess. As a live run
  (compiled binary + agent + `lldb`), it ships gated/deferred per Foundry's live-eval discipline.
- AC-3.3 A deterministic grader unit test SHALL prove the discrimination against two canned
  transcripts — a debugger-used run (breakpoint hit + frame/variable inspected) passes; a
  static-only correct guess fails — so discrimination is gate-proven without the live run. It
  runs in `check-fast` via a `tests/grade_debug_test.sh` shim (the `tests/*_test.sh` glob the gate
  discovers) over `evals/harness/test_grade_debug.py`, beside its grader `evals/harness/grade_debug.py`
  — the established `grade_*.py` + `test_grade_*.py` + shim pattern.

## US-4 — Placement + knowledge

- AC-4.1 THE skill SHALL live at `plugins/foundry/skills/debug/` with `references/` for the
  `lldb` cheatsheet, the `lldb`↔`gdb` map, and the seeded-bug walkthrough.
- AC-4.2 `knowledge/log.md` SHALL record the skill; no glossary row is added (standard debugger
  vocabulary; prior art the LLDB/GDB docs).

## Metrics

- A skill-guided agent sets a breakpoint at the suspect site, hits it, inspects the
  frame/variable, and names the faulting line — on a seeded bug it could not trivially spot by
  reading the source.
- Discrimination: a run that never invokes the debugger fails the eval even if it guesses right.
