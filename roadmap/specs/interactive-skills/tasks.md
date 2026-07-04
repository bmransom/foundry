> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# interactive-skills — tasks

Waves are ordered; tasks within a wave are independent. Each names the gate that proves it.

## Wave 1 — the bridge

- **T1** `foundry rubric [<stage>]` CLI subcommand: stage map (no arg) from `stages.py`; one
  stage's rubric verbatim via `load_rubric`; mechanical stage → note + gate; unknown → error.
  *Gate: `tests/test_cli.py` (map, verbatim == load_rubric, mechanical, unknown).*

## Wave 2 — the skills

- **T2** `code` (orchestrator), `spec-review`, `code-review`, `knowledge` (thin, fetch
  `foundry rubric <stage>`); `handoff` restored near-verbatim + `spawn-successor.sh`. *Gate:
  `plugin_skills_test.sh`, `skill_references_test.sh`, `context_budget_test.sh`, manifest
  validate.*

## Wave 3 — close

- **T3** One positive triggering case per restored skill in
  `evals/fixtures/triggering/cases.json`. *Gate: `triggering_eval_test.sh` (hermetic).*
- **T4** Knowledge: `log.md` entry (skills restored, single-sourced via `foundry rubric`);
  board row. *Gate: `foundry gate`.*
- **T5** Fresh-context `code-review`; apply findings. Live triggering-eval run (opt-in) as
  verification. *Gate: `CODE_REVIEW: PASS`.*
