> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# interactive-skills — design

Restore the interactive skill layer v2 deleted, as the supervised counterpart to the driver.
Two modes, side by side: the **skills** (current agent walks the work in your session) and
the **driver** (`foundry run`/`review`, headless, ledgered). v2 built the driver well and
erased the skills; this puts them back, refined to single-source their judgment.

## Decisions

- **D1 Stage skills fetch judgment; they don't carry it.** `spec-review`, `code-review`,
  `knowledge`, and `code` pull their rubric from `.foundry/bin/foundry rubric <stage>` — the
  same text the driver compiles. The deleted v1 skills embedded judgment as prose that then
  had to be re-extracted into rubrics; fetching keeps one source, two consumers, no drift.
- **D2 `foundry rubric` is the bridge.** The rubrics are package-internal; a session reaches
  them only through the CLI, and the CLI only through the `.foundry/bin/foundry` shim (conv 6,
  the prerequisite). `rubric` with no arg prints the ordered stage map from `stages.py`;
  `rubric <stage>` prints the rubric via the driver's own `load_rubric` (byte-identical).
- **D3 `code` orchestrates; the stage skills carry the workflow.** As the original did, `code`
  stays a thin sequencer and defers each judgment stage to its lower-level skill (or the
  rubric). It does **not** invoke `foundry run` — that would spawn headless stage-sessions and
  discard the shared context that is the whole point of the interactive mode.
- **D4 `handoff` is restored near-verbatim.** Its judgment is a workflow, not a rubric, so it
  has no driver twin. The fresh-session runner (`plugins/foundry/scripts/spawn-fresh-session.sh`)
  survived the v1 purge; only the skill wrapper and its `spawn-successor.sh` rider were
  deleted. Both come back unchanged — they already target `.agent/handoff/HANDOFF.md`.
- **D5 Names reclaimed deliberately.** `code`/`handoff`/`spec-review`/`code-review`/`knowledge`
  return to their original names — the maintainer's muscle memory. No collision: the
  deterministic lifecycle is the `foundry run` CLI, not a skill. `code-review` the skill is
  distinct from the generic `/code-review` (quality sweep) and `foundry review <pr>` (headless
  PR review); the skill's body states the distinction.

## Public surface

| Surface | Change |
|---|---|
| `foundry rubric [<stage>]` (CLI) | new subcommand: stage map, or one stage's rubric verbatim; unknown stage errors |
| `plugins/foundry/skills/code/SKILL.md` | interactive lifecycle orchestrator (supervised) |
| `plugins/foundry/skills/{spec-review,code-review,knowledge}/SKILL.md` | thin stage skills, judgment fetched via `foundry rubric` |
| `plugins/foundry/skills/handoff/{SKILL.md,scripts/spawn-successor.sh}` | restored near-verbatim |
| `evals/fixtures/triggering/cases.json` | one positive triggering case per restored skill |

## Invariants

- No stage skill contains its stage's judgment inline — it fetches `foundry rubric <stage>`;
  the rubric text lives once, in `src/foundry/rubrics/`.
- `foundry rubric <stage>` output equals `load_rubric(stage)` (the driver's compile source).
- `code` never invokes `foundry run`; the supervised path shares the session's context and
  claims no determinism.
- The skills load under the plugin/context-budget/reference validators the gate runs.
- `handoff`'s `spawn-successor.sh` resolves the surviving runner at
  `plugins/foundry/scripts/spawn-fresh-session.sh` (its `../../..` plugin-root walk).

## Metrics

The triggering eval (each restored skill has a positive case) is the discrimination signal —
graded live against fresh `claude -p` classifications, baseline = the pre-restoration skill
set. N/A for the skills' prose quality (subjective, per skill-creator).

## Two-mode map

| Want | Invoke | Who works |
|---|---|---|
| Pair in this session | the `code` skill (and its stage siblings) | the current agent, in context |
| Unattended, ledgered | `.foundry/bin/foundry run <card>` / `review <pr>` | the driver's spawned sessions |
