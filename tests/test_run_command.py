"""Tests for foundry.run_command (T7/T8): `foundry run <card-id>` end-to-end.

A scripted FakeAdapter drives a bug-fix path run on a pytest repo fixture. Asserts
the ledger event sequence (run_started … run_completed), the worktree/branch got
created, the entry path is persisted, and NO commit landed on the default branch
(AC-1.8). Unknown-card error test with near-match suggestion (AC-1.1).

T8 extends this: `resume()` reconstructs a halted run from the ledger alone
(AC-1.6), and `run(..., interactive=True)` routes judgment/mixed stages through
the adapter's interactive command, still gated on exit (AC-1.5).
"""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from foundry.adapters.parsers import StageResult
from foundry.board import BoardError
from foundry.config import Config
from foundry.driver.machine import GateContext
from foundry.ledger import RunLedger
from foundry.run_command import RunNotFoundError, build_gates, resume, run

FIXED = datetime(2026, 7, 2, 17, 0, 0, tzinfo=timezone.utc)


class FakeAdapter:
    """Records judgment/mixed calls; returns marker text the stage gates parse."""

    def __init__(self):
        self.calls = []

    def __call__(self, stage, route, workspace):
        self.calls.append(stage)
        text = ""
        if stage == "spec":
            text = "SPEC_REVIEW: CLEAN"
        elif stage == "review":
            text = "CODE_REVIEW: PASS"
        return StageResult(text=text, input_tokens=100, output_tokens=10, exit_status=0)


def test_bug_fix_run_end_to_end(tmp_path, repo_factory, git_probes):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    before = git_probes["head_sha"](repo, "main")

    adapter = FakeAdapter()
    result = run(
        "wclip-paste",
        repo_root=repo,
        path="bug-fix",
        adapter=adapter,
        now=lambda: FIXED,
    )

    assert result.outcome == "completed"

    # worktree + branch created off the default branch
    assert (repo / "wt" / "wclip-paste").is_dir()
    assert git_probes["branch_exists"](repo, "card/wclip-paste")

    # ledger rooted at the repo; event sequence run_started … run_completed
    from foundry.ledger import RunLedger

    events = RunLedger(repo).events(result.run_id)
    names = [e.event for e in events]
    assert names[0] == "run_started"
    assert names[-1] == "run_completed"
    # bug-fix skips frame/spec/plan; adapter fires for build/knowledge/review
    assert adapter.calls == ["build", "knowledge", "review"]

    # entry path persisted on run_started (resume reads this, not Driver config)
    assert events[0].stage == "bug-fix"

    # AC-1.8: no commit landed on the default branch
    assert git_probes["head_sha"](repo, "main") == before


def test_worktree_is_reused_when_present(tmp_path, repo_factory):
    repo = repo_factory(tmp_path)
    r1 = run("wclip-paste", repo_root=repo, path="bug-fix", adapter=FakeAdapter(), now=lambda: FIXED)
    # second run reuses wt/<id> and its branch rather than re-creating
    r2 = run("wclip-paste", repo_root=repo, path="bug-fix", adapter=FakeAdapter(), now=lambda: FIXED)
    assert r1.outcome == "completed" and r2.outcome == "completed"
    assert (repo / "wt" / "wclip-paste").is_dir()


def test_unknown_card_errors_with_near_match(tmp_path, repo_factory):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    with pytest.raises(BoardError) as excinfo:
        run("wclip-past", repo_root=repo, path="bug-fix", adapter=FakeAdapter())
    assert "wclip-paste" in str(excinfo.value)


# --- T8: resume (AC-1.6) -------------------------------------------------------


class SpecFailingAdapter:
    """Always fails the spec-stage marker gate, driving the run to RETRY_CAP halt."""

    def __init__(self):
        self.calls = []

    def __call__(self, stage, route, workspace):
        self.calls.append(stage)
        text = "SPEC_REVIEW: FAIL" if stage == "spec" else ""
        return StageResult(text=text, input_tokens=10, output_tokens=1, exit_status=0)


class ResumeAdapter:
    """Passes every stage's marker gate; used to complete a run after resume."""

    def __init__(self):
        self.calls = []

    def __call__(self, stage, route, workspace):
        self.calls.append(stage)
        text = ""
        if stage == "spec":
            text = "SPEC_REVIEW: CLEAN"
        elif stage == "review":
            text = "CODE_REVIEW: PASS"
        return StageResult(text=text, input_tokens=10, output_tokens=1, exit_status=0)


def test_resume_continues_after_halt_at_the_right_stage(tmp_path, repo_factory):
    # feature path reaches plan; the plan gate needs tasks.md in place (design D1).
    repo = repo_factory(
        tmp_path, cards=[("wclip-paste", "Paste command")], tasks_md_for=["wclip-paste"]
    )

    halted = run(
        "wclip-paste", repo_root=repo, path="feature",
        adapter=SpecFailingAdapter(), now=lambda: FIXED,
    )
    assert halted.outcome == "halted"
    assert halted.halted_gate == "SPEC_REVIEW"

    resumed = resume(halted.run_id, repo_root=repo, adapter=ResumeAdapter(), now=lambda: FIXED)
    assert resumed.outcome == "completed"

    events = RunLedger(repo).events(halted.run_id)
    names = [e.event for e in events]
    assert names[0] == "run_started"
    assert names[-1] == "run_completed"
    assert "run_resumed" in names
    # resume picked up right after "frame" (the last completed boundary), not from scratch
    assert "frame" not in resumed.stages_started

    completed_stages = [e.stage for e in events if e.event == "stage_completed"]
    assert len(completed_stages) == len(set(completed_stages))  # no stage completes twice


def test_resume_unknown_run_id_errors_listing_known_runs(tmp_path, repo_factory):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    known = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        adapter=FakeAdapter(), now=lambda: FIXED,
    )

    with pytest.raises(RunNotFoundError) as excinfo:
        resume("r-does-not-exist", repo_root=repo)
    assert known.run_id in str(excinfo.value)


def test_resume_already_complete_is_a_short_circuit(tmp_path, repo_factory):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    completed = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        adapter=FakeAdapter(), now=lambda: FIXED,
    )
    assert completed.outcome == "completed"

    result = resume(completed.run_id, repo_root=repo)
    assert result.outcome == "already_complete"

    # no new events appended past run_completed
    events = RunLedger(repo).events(completed.run_id)
    assert events[-1].event == "run_completed"


# --- T8: interactive (AC-1.5) ---------------------------------------------------


class RecordingInteractiveRun:
    """Stub interactive runner: records (argv, workspace), returns a fixed exit code."""

    def __init__(self, returncode=0):
        self.calls = []
        self.returncode = returncode

    def __call__(self, argv, workspace):
        self.calls.append((argv, workspace))
        return self.returncode


def test_interactive_launches_stub_command_and_gate_passes_the_transition(tmp_path, repo_factory):
    # gate_test="true": build's command gate (config.gate_test) is what decides
    # the transition — not the captured session text, since none is captured.
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")], gate_test="true")
    interactive_run = RecordingInteractiveRun(returncode=0)

    result = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        interactive=True, interactive_run=interactive_run, now=lambda: FIXED,
    )

    # build's gate passed on the first interactive call (no retry there) and the
    # run advanced to knowledge (mixed, also interactive) before halting at
    # review — review's marker gate needs captured text an inherited-stdio
    # session cannot supply; a documented limitation, not a bug (AC-1.5 covers
    # command-gated stages; marker-gated stages need a future capture story).
    assert result.halted_gate == "CODE_REVIEW"
    assert len(interactive_run.calls) >= 2  # build, then knowledge, both ran interactively
    argv, workspace = interactive_run.calls[0]
    assert argv  # non-empty argv shape (harness [interactive].command, expanded)
    assert workspace.endswith(str(Path("wt") / "wclip-paste"))


def test_interactive_session_exit_does_not_bypass_the_gate(tmp_path, repo_factory):
    # gate_test="false": build's command gate always fails, regardless of the
    # interactive session's own exit code (0) — the gate, not the session, decides.
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")], gate_test="false")
    interactive_run = RecordingInteractiveRun(returncode=0)

    result = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        interactive=True, interactive_run=interactive_run, now=lambda: FIXED,
    )

    assert result.outcome == "halted"
    assert result.halted_gate == "tests"
    assert len(interactive_run.calls) == 3  # RETRY_CAP attempts, each launching the session


# --- T10: CLI flag layer (AC-3.1/AC-3.2) ---------------------------------------


def test_cli_flags_override_route_and_ledger_records_resolved_route(tmp_path, repo_factory):
    # no [routing] table in the fixture config: shipped defaults would otherwise
    # route build -> claude-code/claude-sonnet-5 (AC-3.1's lower layers).
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])

    result = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        adapter=FakeAdapter(), now=lambda: FIXED,
        harness="codex", model="gpt-5.5", effort="high",
    )
    assert result.outcome == "completed"

    events = RunLedger(repo).events(result.run_id)
    build_completed = next(
        e for e in events if e.event == "stage_completed" and e.stage == "build"
    )
    assert build_completed.harness == "codex"
    assert build_completed.model == "gpt-5.5"
    assert build_completed.effort == "high"


def test_no_cli_flags_falls_back_to_shipped_default_route(tmp_path, repo_factory):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])

    result = run(
        "wclip-paste", repo_root=repo, path="bug-fix",
        adapter=FakeAdapter(), now=lambda: FIXED,
    )
    assert result.outcome == "completed"

    events = RunLedger(repo).events(result.run_id)
    build_completed = next(
        e for e in events if e.event == "stage_completed" and e.stage == "build"
    )
    assert build_completed.harness == "claude-code"
    assert build_completed.model == "claude-sonnet-5"
    assert build_completed.effort is None


# --- plan gate: tasks.md existence (design D1) ---------------------------------


def test_plan_gate_fails_when_tasks_md_missing(tmp_path):
    gates = build_gates(Config(), spec="roadmap/specs/demo-feature/")
    outcome = gates["plan"](GateContext(tmp_path, None))
    assert outcome.outcome == "FAIL"


def test_plan_gate_passes_when_tasks_md_present(tmp_path):
    spec_dir = tmp_path / "roadmap" / "specs" / "demo-feature"
    spec_dir.mkdir(parents=True)
    (spec_dir / "tasks.md").write_text("# tasks\n")

    gates = build_gates(Config(), spec="roadmap/specs/demo-feature/")
    outcome = gates["plan"](GateContext(tmp_path, None))
    assert outcome.outcome == "PASS"


def test_plan_gate_fails_when_spec_cell_blank():
    gates = build_gates(Config(), spec="")
    outcome = gates["plan"](GateContext(None, None))
    assert outcome.outcome == "FAIL"


def test_default_interactive_runner_inherits_stdio(monkeypatch):
    """No stub injected: the real runner must not capture stdout/stderr (AC-1.5)."""
    from foundry import run_command

    calls = []
    real_subprocess_run = run_command.subprocess.run

    def spy(argv, **kwargs):
        calls.append(kwargs)
        return real_subprocess_run(argv, **kwargs)

    monkeypatch.setattr(run_command.subprocess, "run", spy)
    returncode = run_command._interactive_subprocess(["true"], ".")

    assert returncode == 0
    assert "capture_output" not in calls[0]
    assert "stdout" not in calls[0]
    assert "stderr" not in calls[0]
