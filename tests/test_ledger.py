"""Tests for foundry.ledger (design D4: wide events, append-only, run ids, cost)."""

import json
import re
from datetime import datetime, timedelta, timezone

import pytest

from foundry.ledger import (
    PRICES,
    PRICES_UPDATED,
    RunEvent,
    RunLedger,
    compute_cost,
    new_run_id,
)

RUN_ID_RE = re.compile(r"^r-\d{14}-[0-9a-f]{4}$")


def make_event(run_id, event, stage=None, **kwargs):
    return RunEvent(
        run_id=run_id,
        card_id="v2-skeleton",
        stage=stage,
        event=event,
        ts="2026-07-02T17:10:04Z",
        **kwargs,
    )


def test_append_only_two_lines_order_preserved(tmp_path):
    ledger = RunLedger(tmp_path)
    run_id = "r-20260702171004-a1b2"
    ledger.append(make_event(run_id, "run_started"))
    ledger.append(make_event(run_id, "stage_started", stage="build"))

    path = tmp_path / ".foundry" / "runs" / run_id / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "run_started"
    assert json.loads(lines[1])["event"] == "stage_started"


def test_append_creates_directories(tmp_path):
    ledger = RunLedger(tmp_path)
    run_id = "r-20260702171004-a1b2"
    assert not (tmp_path / ".foundry").exists()
    ledger.append(make_event(run_id, "run_started"))
    assert (tmp_path / ".foundry" / "runs" / run_id / "events.jsonl").exists()


def test_round_trip_parse(tmp_path):
    ledger = RunLedger(tmp_path)
    run_id = "r-20260702171004-a1b2"
    original = make_event(
        run_id,
        "stage_completed",
        stage="build",
        harness="claude-code",
        model="claude-sonnet-5",
        effort=None,
        input_tokens=91234,
        output_tokens=8123,
        cost_usd=1.87,
        duration_s=412,
        gate={"name": "tests", "outcome": "PASS"},
    )
    ledger.append(original)

    [parsed] = ledger.events(run_id)
    assert parsed == original


def test_last_boundary_picks_latest_stage_completed(tmp_path):
    ledger = RunLedger(tmp_path)
    run_id = "r-20260702171004-a1b2"
    ledger.append(make_event(run_id, "run_started"))
    ledger.append(make_event(run_id, "stage_completed", stage="spec"))
    ledger.append(make_event(run_id, "stage_started", stage="build"))
    ledger.append(make_event(run_id, "stage_completed", stage="build"))
    ledger.append(make_event(run_id, "stage_started", stage="review"))

    boundary = ledger.last_boundary(run_id)
    assert boundary is not None
    assert boundary.event == "stage_completed"
    assert boundary.stage == "build"


def test_last_boundary_none_when_absent(tmp_path):
    ledger = RunLedger(tmp_path)
    run_id = "r-20260702171004-a1b2"
    ledger.append(make_event(run_id, "run_started"))
    ledger.append(make_event(run_id, "stage_started", stage="spec"))

    assert ledger.last_boundary(run_id) is None


def test_last_boundary_none_for_unknown_run(tmp_path):
    ledger = RunLedger(tmp_path)
    assert ledger.last_boundary("r-does-not-exist-0000") is None


def test_run_id_format():
    run_id = new_run_id()
    assert RUN_ID_RE.match(run_id), run_id


def test_run_id_unique_across_timestamps():
    # Same-second draws are only entropy-unique (16 bits — collisions allowed);
    # the guaranteed axis is the timestamp.
    base = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)
    ids = {new_run_id(now=base + timedelta(seconds=i)) for i in range(50)}
    assert len(ids) == 50


def test_cost_math_known_model_opus():
    cost = compute_cost("claude-opus-4-8", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == pytest.approx(15.0 + 75.0)


def test_cost_math_known_model_sonnet():
    cost = compute_cost("claude-sonnet-5", input_tokens=200_000, output_tokens=100_000)
    # 200k/1e6 * 3 + 100k/1e6 * 15 = 0.6 + 1.5
    assert cost == pytest.approx(2.1)


def test_cost_unknown_model_returns_none():
    assert compute_cost("gpt-5.5", input_tokens=1000, output_tokens=1000) is None


def test_price_table_has_prices_updated_date():
    assert isinstance(PRICES_UPDATED, str) and PRICES_UPDATED
    assert "claude-opus-4-8" in PRICES
    assert "claude-sonnet-5" in PRICES


def test_runs_listing_sums_cost(tmp_path):
    ledger = RunLedger(tmp_path)

    run_a = "r-20260702171004-a1b2"
    ledger.append(make_event(run_a, "run_started"))
    ledger.append(
        make_event(
            run_a,
            "stage_completed",
            stage="build",
            model="claude-sonnet-5",
            cost_usd=1.5,
        )
    )
    ledger.append(
        make_event(
            run_a,
            "stage_completed",
            stage="review",
            model="claude-sonnet-5",
            cost_usd=0.5,
        )
    )
    ledger.append(make_event(run_a, "run_completed"))

    run_b = "r-20260702171500-c3d4"
    ledger.append(make_event(run_b, "run_started"))
    ledger.append(
        make_event(
            run_b,
            "stage_completed",
            stage="build",
            model="unknown-model",
            cost_usd=None,
        )
    )
    ledger.append(make_event(run_b, "run_halted"))

    summaries = {s.run_id: s for s in ledger.list_runs()}
    assert summaries[run_a].outcome == "run_completed"
    assert summaries[run_a].total_cost_usd == pytest.approx(2.0)
    assert summaries[run_b].outcome == "run_halted"
    assert summaries[run_b].total_cost_usd == pytest.approx(0.0)
