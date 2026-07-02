"""Tests for foundry.runs_command (AC-4.3/AC-4.4): `foundry runs list` / `runs show`.

`list_lines` renders one line per run (run id, outcome, cost); `show_lines` renders
the run's stage table, one row per `stage_completed` event. Both are read-only views
over `RunLedger` — no ledger writes.
"""

import pytest

from foundry.ledger import RunEvent, RunLedger
from foundry.runs_command import RunNotFoundError, _format_cost, list_lines, show_lines


def make_event(run_id, event, stage=None, **kwargs):
    return RunEvent(
        run_id=run_id,
        card_id="v2-driver",
        stage=stage,
        event=event,
        ts="2026-07-02T17:10:04Z",
        **kwargs,
    )


# --- cost formatting -----------------------------------------------------------


def test_format_cost_dollars_when_known():
    assert _format_cost(1.87) == "$1.87"


def test_format_cost_dash_when_none():
    assert _format_cost(None) == "-"


# --- runs list (AC-4.3) ---------------------------------------------------------


def test_list_lines_shows_run_id_outcome_and_cost(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(make_event("r-a", "run_started"))
    ledger.append(
        make_event("r-a", "stage_completed", stage="build", model="claude-sonnet-5", cost_usd=1.87)
    )
    ledger.append(make_event("r-a", "run_completed"))

    assert list_lines(tmp_path) == ["r-a run_completed $1.87"]


def test_list_lines_one_line_per_run_no_runs_is_empty(tmp_path):
    assert list_lines(tmp_path) == []


# --- runs show (AC-4.4) ----------------------------------------------------------


def test_show_lines_one_row_per_stage_completed(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(make_event("r-a", "run_started"))
    ledger.append(make_event("r-a", "stage_started", stage="build"))
    ledger.append(
        make_event(
            "r-a", "stage_completed", stage="build",
            harness="claude-code", model="claude-sonnet-5",
            input_tokens=91234, output_tokens=8123, cost_usd=1.87, duration_s=412.3,
            gate={"name": "tests", "outcome": "PASS"},
        )
    )
    ledger.append(make_event("r-a", "run_completed"))

    lines = show_lines(tmp_path, "r-a")
    # header + separator + exactly one data row (stage_started/run_started/run_completed excluded)
    assert len(lines) == 3
    row = lines[2]
    assert "build" in row
    assert "claude-code" in row
    assert "claude-sonnet-5" in row
    assert "91234" in row
    assert "8123" in row
    assert "$1.87" in row
    assert "412.3" in row
    assert "PASS" in row


def test_show_lines_cost_none_renders_as_dash(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(make_event("r-a", "run_started"))
    ledger.append(
        make_event(
            "r-a", "stage_completed", stage="build",
            model="unknown-model", input_tokens=10, output_tokens=1, cost_usd=None,
            gate={"name": "tests", "outcome": "PASS"},
        )
    )
    ledger.append(make_event("r-a", "run_completed"))

    lines = show_lines(tmp_path, "r-a")
    assert " - " in lines[2] or lines[2].split()[-2] == "-"


def test_show_lines_unknown_run_id_raises_listing_known_ids(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(make_event("r-known", "run_started"))
    ledger.append(make_event("r-known", "run_completed"))

    with pytest.raises(RunNotFoundError) as excinfo:
        show_lines(tmp_path, "r-does-not-exist")
    assert "r-known" in str(excinfo.value)


def test_show_lines_no_runs_at_all_lists_none_recorded(tmp_path):
    with pytest.raises(RunNotFoundError) as excinfo:
        show_lines(tmp_path, "r-does-not-exist")
    assert "no runs recorded" in str(excinfo.value)
