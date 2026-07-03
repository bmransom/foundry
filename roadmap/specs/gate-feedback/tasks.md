> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# gate-feedback — tasks

Waves are ordered; tasks within a wave are independent. Each task names the gate that
proves it.

## Wave 0 — contract

- **T0** Add the Scenario to `features/run.feature` (process contract): a failed build
  gate's evidence reaches the second attempt's prompt and the ledger keeps the stage's
  returned text. Red first via T1–T3's tests. *Gate: `uv run pytest -q` (red → green
  across the waves).*

## Wave 1 — evidence in gates (machine.py)

- **T1** `GateOutcome.detail` + `GateFeedback` + caps: test that `command_gate` on a
  failing command yields `detail` = capped output tail (and still writes output to
  stdout), `marker_gate` yields the seen value / "no marker line", the plan gate the
  missing path. Tests in `tests/test_machine.py` and `tests/test_run_command.py` land
  red; `src/foundry/driver/machine.py` + `run_command._plan_gate` turn them green.
  *Gate: `uv run pytest -q`.*

## Wave 2 — feedback through the retry loop

- **T2** `_run_with_retry` passes `GateFeedback(gate, attempt, detail)` to the adapter
  on attempts ≥ 2; review FAIL → build re-entry passes the review tail
  (`tests/test_machine.py`: a recording fake adapter asserts attempt 1 gets None,
  attempt 2 gets the prior FAIL's detail; the review loop-back case asserts build's
  feedback carries the review text). `Adapter` Protocol and `run_command._make_adapter`
  widen to accept `feedback`. *Gate: `uv run pytest -q`.*

## Wave 3 — prompt + ledger

- **T3** `compile_stage_prompt(..., feedback=)` renders the
  `## Previous attempt failed its gate` section between rubrics and card context;
  no-feedback output is byte-identical to today (`tests/test_prompts.py`).
  *Gate: `uv run pytest -q`.*
- **T4** `RunEvent.result_text` + machine records the capped tail on `gate_evaluated`;
  a pre-change event line (no `result_text` key) still parses
  (`tests/test_ledger.py`, `tests/test_machine.py`). *Gate: `uv run pytest -q`.*

## Wave 4 — rubric + close

- **T5** `rubrics/build.md`: Output contract instructs running the repo's test command
  and finishing only at exit 0; `validate_rubric` stays green (test asserts the shipped
  rubric loads). *Gate: `uv run pytest -q`.*
- **T6** Knowledge: glossary entry **Gate feedback**; `knowledge/log.md` entry;
  regenerate `index.md`. Board row for `gate-feedback` under Epic 8.
  *Gate: `uv run foundry gate`.*
- **T7** Fresh-context code review; fix blocking findings. *Gate: CODE_REVIEW: PASS.*
