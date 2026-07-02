"""Tests for foundry.driver.machine (T5): the deterministic state machine.

Covers AC-1.2 (gate blocks transition), AC-1.4 (RETRY_CAP halt), review
loop-back + round ceiling, entry maps, stage hooks (AC-1.9), resume (AC-1.6),
happy-path ledger order, and autonomy ask (AC-1.7). Adapter and gates are fakes.
"""

import os
import stat
from datetime import datetime, timezone

import pytest

from foundry.config import Config
from foundry.ledger import RunLedger
from foundry.driver.machine import (
    AutonomyError,
    AutonomyPolicy,
    Driver,
    GateContext,
    GateOutcome,
    StageResult,
    command_gate,
    marker_gate,
)
from foundry.driver.stages import (
    ENTRY_PATHS,
    REVIEW_ROUND_CEILING,
    RETRY_CAP,
    STAGE_ORDER,
    stages_for,
)

FIXED = datetime(2026, 7, 2, 17, 0, 0, tzinfo=timezone.utc)


class FakeAdapter:
    """Records judgment-stage calls; returns a StageResult per stage."""

    def __init__(self, results=None):
        self.calls = []
        self._results = results or {}

    def __call__(self, stage, route, workspace):
        self.calls.append(stage)
        return self._results.get(
            stage, StageResult(text="", input_tokens=100, output_tokens=10)
        )


def pass_gate(name):
    return lambda ctx: GateOutcome(name, "PASS")


def fail_gate(name):
    return lambda ctx: GateOutcome(name, "FAIL")


def all_pass_gates():
    return {name: pass_gate(name) for name in STAGE_ORDER}


def make_driver(tmp_path, **overrides):
    ledger = RunLedger(tmp_path)
    adapter = overrides.pop("adapter", FakeAdapter())
    gates = overrides.pop("gates", all_pass_gates())
    autonomy = overrides.pop("autonomy", AutonomyPolicy("autonomous", "card"))
    kwargs = dict(
        workspace=tmp_path,
        ledger=ledger,
        card_id="v2-driver",
        adapter=adapter,
        gates=gates,
        autonomy=autonomy,
        config=Config(),
        path="feature",
        now=lambda: FIXED,
    )
    kwargs.update(overrides)
    return Driver(**kwargs), ledger, adapter


def names(ledger, run_id):
    return [(e.event, e.stage) for e in ledger.events(run_id)]


def events_named(ledger, run_id, event):
    return [e for e in ledger.events(run_id) if e.event == event]


def write_hook(tmp_path, stage, phase, code, executable=True):
    hooks = tmp_path / ".foundry" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    path = hooks / f"{stage}.{phase}.sh"
    path.write_text(f"#!/bin/sh\nexit {code}\n")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


# --- gate factories (AC-10.2) -------------------------------------------------


def test_marker_gate_parses_declared_last_line_marker():
    gate = marker_gate("CODE_REVIEW", "CODE_REVIEW", "PASS")
    clean = StageResult(text="findings...\nCODE_REVIEW: PASS")
    dirty = StageResult(text="findings...\nCODE_REVIEW: FAIL")
    assert gate(GateContext(None, clean)).outcome == "PASS"
    assert gate(GateContext(None, dirty)).outcome == "FAIL"


def test_marker_gate_last_marker_wins_and_missing_is_fail():
    gate = marker_gate("SPEC_REVIEW", "SPEC_REVIEW", "CLEAN")
    multi = StageResult(text="SPEC_REVIEW: DIRTY\ntail\nSPEC_REVIEW: CLEAN")
    assert gate(GateContext(None, multi)).outcome == "PASS"
    assert gate(GateContext(None, StageResult(text="no marker"))).outcome == "FAIL"


def test_command_gate_passes_on_exit_zero(tmp_path):
    ok = command_gate("tests", ["sh", "-c", "exit 0"])
    bad = command_gate("tests", ["sh", "-c", "exit 1"])
    assert ok(GateContext(tmp_path, None)).outcome == "PASS"
    assert bad(GateContext(tmp_path, None)).outcome == "FAIL"


# --- entry maps ---------------------------------------------------------------


def test_entry_maps_skip_stages_per_path():
    assert [s.name for s in stages_for("feature")] == list(STAGE_ORDER)
    assert [s.name for s in stages_for("bug-fix")][0] == "build"
    assert [s.name for s in stages_for("refactor")][0] == "build"
    assert [s.name for s in stages_for("enhancement")][0] == "spec"
    assert ENTRY_PATHS["refactor"].feature_file_check is False
    assert ENTRY_PATHS["enhancement"].light_spec is True


def test_bug_fix_run_never_enters_earlier_stages(tmp_path):
    driver, ledger, adapter = make_driver(tmp_path, path="bug-fix")
    result = driver.run()
    started = [s for (e, s) in names(ledger, result.run_id) if e == "stage_started"]
    assert "frame" not in started and "spec" not in started and "plan" not in started
    assert started[0] == "build"
    assert result.outcome == "completed"


# --- happy path ---------------------------------------------------------------


def test_happy_path_ledger_sequence(tmp_path):
    driver, ledger, adapter = make_driver(tmp_path)
    result = driver.run()
    seq = [e for (e, s) in names(ledger, result.run_id)]
    expected = ["run_started"]
    for _ in STAGE_ORDER:
        expected += ["stage_started", "gate_evaluated", "stage_completed"]
    expected += ["run_completed"]
    assert seq == expected
    assert result.outcome == "completed"
    # judgment/mixed stages call the adapter; mechanical do not
    assert adapter.calls == ["spec", "plan", "build", "knowledge", "review"]


# --- gate blocks transition + retry halt --------------------------------------


def test_failed_gate_blocks_next_stage(tmp_path):
    gates = all_pass_gates()
    gates["frame"] = fail_gate("frame")
    driver, ledger, adapter = make_driver(tmp_path, gates=gates)
    result = driver.run()
    started = [s for (e, s) in names(ledger, result.run_id) if e == "stage_started"]
    assert started == ["frame"]  # next stage (spec) never entered
    assert result.outcome == "halted"


def test_retry_cap_halts_with_run_halted_naming_gate(tmp_path):
    gates = all_pass_gates()
    gates["spec"] = fail_gate("SPEC_REVIEW")
    driver, ledger, adapter = make_driver(tmp_path, gates=gates)
    result = driver.run()
    spec_fails = [
        e for e in events_named(ledger, result.run_id, "gate_evaluated")
        if e.stage == "spec"
    ]
    assert len(spec_fails) == RETRY_CAP
    assert adapter.calls.count("spec") == RETRY_CAP
    halted = events_named(ledger, result.run_id, "run_halted")
    assert len(halted) == 1
    assert halted[0].gate["name"] == "SPEC_REVIEW"
    assert result.outcome == "halted"
    assert result.halted_gate == "SPEC_REVIEW"


# --- review loop-back + ceiling -----------------------------------------------


def test_review_fail_loops_back_to_build_then_passes(tmp_path):
    state = {"n": 0}

    def review_gate(ctx):
        state["n"] += 1
        return GateOutcome("CODE_REVIEW", "FAIL" if state["n"] == 1 else "PASS")

    gates = all_pass_gates()
    gates["review"] = review_gate
    driver, ledger, adapter = make_driver(tmp_path, gates=gates)
    result = driver.run()
    build_starts = [
        e for e in events_named(ledger, result.run_id, "stage_started")
        if e.stage == "build"
    ]
    assert len(build_starts) == 2  # initial + one loop-back
    assert result.outcome == "completed"


def test_review_round_ceiling_halts(tmp_path):
    gates = all_pass_gates()
    gates["review"] = fail_gate("CODE_REVIEW")
    driver, ledger, adapter = make_driver(tmp_path, gates=gates)
    result = driver.run()
    build_starts = [
        e for e in events_named(ledger, result.run_id, "stage_started")
        if e.stage == "build"
    ]
    assert len(build_starts) == REVIEW_ROUND_CEILING
    assert result.outcome == "halted"
    assert result.halted_gate == "CODE_REVIEW"


# --- stage hooks (AC-1.9) -----------------------------------------------------


def test_failing_pre_hook_blocks_stage_entry(tmp_path):
    write_hook(tmp_path, "spec", "pre", 1)
    driver, ledger, adapter = make_driver(tmp_path)
    result = driver.run()
    started = [s for (e, s) in names(ledger, result.run_id) if e == "stage_started"]
    assert "spec" not in started  # entry blocked
    assert "spec" not in adapter.calls
    hook_evs = events_named(ledger, result.run_id, "hook_evaluated")
    assert any(h.gate["outcome"] == "FAIL" for h in hook_evs)
    assert result.outcome == "halted"


def test_failing_post_hook_fails_the_gate(tmp_path):
    write_hook(tmp_path, "build", "post", 1)
    driver, ledger, adapter = make_driver(tmp_path, path="bug-fix")
    result = driver.run()
    build_gate = [
        e for e in events_named(ledger, result.run_id, "gate_evaluated")
        if e.stage == "build"
    ]
    assert build_gate and all(e.gate["outcome"] == "FAIL" for e in build_gate)
    assert len(build_gate) == RETRY_CAP  # gate fails each attempt then halts
    assert any(
        h.gate["name"].startswith("build.post")
        for h in events_named(ledger, result.run_id, "hook_evaluated")
    )
    assert result.outcome == "halted"


def test_non_executable_hook_is_skipped(tmp_path):
    write_hook(tmp_path, "build", "pre", 1, executable=False)
    driver, ledger, adapter = make_driver(tmp_path, path="bug-fix")
    result = driver.run()
    assert events_named(ledger, result.run_id, "hook_evaluated") == []
    assert result.outcome == "completed"


def test_passing_hooks_emit_events_and_run_with_workspace_cwd(tmp_path):
    # a post hook that writes a marker file into cwd proves cwd == workspace
    hooks = tmp_path / ".foundry" / "hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    hook = hooks / "build.post.sh"
    hook.write_text("#!/bin/sh\ntouch ran_here\nexit 0\n")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
    driver, ledger, adapter = make_driver(tmp_path, path="bug-fix")
    result = driver.run()
    assert (tmp_path / "ran_here").exists()
    assert result.outcome == "completed"


# --- resume (AC-1.6) ----------------------------------------------------------


def test_resume_continues_from_last_boundary(tmp_path):
    gates = all_pass_gates()
    gates["build"] = fail_gate("tests")
    driver, ledger, adapter = make_driver(tmp_path, gates=gates)
    first = driver.run()
    assert first.outcome == "halted"
    assert ledger.last_boundary(first.run_id).stage == "plan"

    resumed_driver, ledger2, _ = make_driver(tmp_path)  # all-pass gates
    result = resumed_driver.resume(first.run_id)
    all_events = ledger.events(first.run_id)
    assert any(e.event == "run_resumed" for e in all_events)
    # stages after the boundary completed on resume
    completed_after = [
        e.stage
        for e in all_events
        if e.event == "stage_completed"
        and all_events.index(e) > _index_of_resume(all_events)
    ]
    assert "build" in completed_after and "finish" in completed_after
    assert result.outcome == "completed"


def _index_of_resume(events):
    for i, e in enumerate(events):
        if e.event == "run_resumed":
            return i
    return -1


# --- autonomy (AC-1.7) --------------------------------------------------------


def test_supervised_asks_at_every_gate_boundary(tmp_path):
    calls = []
    driver, ledger, adapter = make_driver(
        tmp_path,
        autonomy=AutonomyPolicy("supervised", "card"),
        ask=lambda stage: calls.append(stage) or True,
    )
    driver.run()
    # asks at every boundary except after the terminal stage
    assert calls == ["frame", "spec", "plan", "build", "verify", "knowledge", "review"]


def test_guided_asks_only_at_plan(tmp_path):
    calls = []
    driver, ledger, adapter = make_driver(
        tmp_path,
        autonomy=AutonomyPolicy("guided", "card"),
        ask=lambda stage: calls.append(stage) or True,
    )
    driver.run()
    assert calls == ["plan"]


def test_autonomous_never_asks(tmp_path):
    calls = []
    driver, ledger, adapter = make_driver(
        tmp_path,
        autonomy=AutonomyPolicy("autonomous", "card"),
        ask=lambda stage: calls.append(stage) or True,
    )
    driver.run()
    assert calls == []


def test_supervised_ask_declined_stops_run(tmp_path):
    driver, ledger, adapter = make_driver(
        tmp_path,
        autonomy=AutonomyPolicy("supervised", "card"),
        ask=lambda stage: False,
    )
    result = driver.run()
    started = [s for (e, s) in names(ledger, result.run_id) if e == "stage_started"]
    assert started == ["frame"]  # declined after frame's boundary
    assert result.outcome == "stopped"


# --- autonomy validation ------------------------------------------------------


def test_invalid_autonomy_level_raises():
    with pytest.raises(AutonomyError):
        AutonomyPolicy("bogus", "card")


def test_invalid_stop_point_raises():
    with pytest.raises(AutonomyError):
        AutonomyPolicy("guided", "bogus")
