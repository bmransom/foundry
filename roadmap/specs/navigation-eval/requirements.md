# Navigation eval — requirements

**Status:** Spec — requirements drafted (2026-06-13) — tracked on the [board](../../ROADMAP.md).

## Overview

A Layer-3 eval that measures whether a context-disclosure approach improves an agent's
navigation of large docs and specs, and a reusable correctness-vs-context-cost
visualization across foundry's evals. The eval compares three **arms** — full-load,
native Read/Grep, and the `docs.py` outline/section protocol — on completeness,
correctness, and efficiency, graded against an independently authored answer key with
decoys. It answers one question with evidence, not intuition: is the
disclosure protocol worth adopting? "Not necessary" is a valid, expected outcome.

## User stories

**US-1 Compare navigation approaches.** As the maintainer, I run the nav-eval and learn
which disclosure arm wins on completeness, correctness, and efficiency.

- AC-1.1 WHEN the nav-eval runs, THE SYSTEM SHALL execute every task under every arm
  (full-load, native Read/Grep, `docs.py` outline/section) for N runs (default N=3).
- AC-1.2 THE SYSTEM SHALL grade each run against an independently authored answer key,
  never the agent's self-report and never a tool that shares code with the arm under test.
- AC-1.3 WHEN a run completes, THE SYSTEM SHALL record, per (task, arm, run): task
  success against the key, context recall (gold spans loaded ÷ gold spans needed),
  context tokens loaded, and tool-call count.
- AC-1.4 THE SYSTEM SHALL plant decoy spans (near-duplicate but wrong) per task and
  SHALL record a decoy hit when an arm's answer relies on a decoy.
- AC-1.5 THE fixture set SHALL span at least three document sizes (≈100, ≈500, ≈2000
  lines) so the report can locate the crossover where the winning arm changes.
- AC-1.6 THE SYSTEM SHALL emit NDJSON to `evals/results/`, one `eval_case` record per
  (task, arm, run) and one `summary` record per arm, matching the existing harness schema.
- AC-1.7 IF an arm's task fixtures are too easy to discriminate (no arm is ever wrong and
  no decoy is ever hit), THE eval SHALL report the fixture set as non-discriminating
  rather than as a pass.

**US-2 Visualize correctness vs context cost.** As the maintainer, I see one chart per
eval plotting correctness against context cost so I can compare arms at a glance.

- AC-2.1 WHEN given an eval's NDJSON results, THE SYSTEM SHALL produce a chart with
  context tokens on the x-axis and correctness on the y-axis, one labelled point per
  arm, written to a committed artifact.
- AC-2.2 THE SYSTEM SHALL produce the chart for each foundry eval whose records carry the
  correctness and context-token fields (the nav-eval, and any existing eval once token
  capture lands).
- AC-2.3 THE chart SHALL mark the Pareto frontier (highest correctness at lowest cost)
  and label each arm.
- AC-2.4 THE visualization SHALL read only NDJSON and SHALL share no code with the evals
  it plots — it consumes results, it is not a grader.

**US-3 Efficiency instrumentation.** As the maintainer, every eval run records its context
cost so efficiency is measurable, not estimated.

- AC-3.1 THE SYSTEM SHALL extract per-run token usage from the headless claude
  `stream-json` transcript and record it in that run's NDJSON.
- AC-3.2 WHERE a result set predates token capture, THE visualization SHALL plot the
  available axis and label the missing cost — never fabricate it.

## Out of scope (v1)

- Statistical-significance claims — N is a smoke-alarm scale, per the existing eval framing.
- The uninstructed-tool arm (tool available but not prompted) and auto-applying the
  discovered threshold — the eval reports the crossover; acting on it is a separate decision.
- Changing `docs.py` or the `code` skill based on results — results-driven, separate spec.
- Any plotting library as a runtime dependency of shipped templates — the viz is
  dev-harness only.

## Dependencies

- The existing eval harness (`evals/harness/`, the NDJSON conventions, the
  `evals/fixtures/<name>/` layout) and the headless `claude` CLI with `--output-format
  stream-json`.
- `docs.py outline`/`section` — the arm under test.

## Open design decisions (resolve in Phase 2)

- **Visualization technology:** stdlib SVG (recommended — matches foundry's zero-dependency
  tooling ethos and embeds in the vitepress site), vs. matplotlib (dev-only dependency,
  easiest), vs. a Vega-Lite spec rendered in the doc site.
- **Context-recall measurement:** how to attribute which gold spans entered the window
  (parse the transcript's tool results / read ranges).
- **Glossary additions** with prior-art provenance: *arm* (experimental design), *context
  recall* (RAG / RAGAS), *gold span*, *context cost*; *decoy* already exists in the
  reviewer fixture.
