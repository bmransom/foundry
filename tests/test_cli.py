"""Tests for foundry.cli."""

import subprocess
import sys

from foundry import __version__
from foundry.ledger import RunEvent, RunLedger


def test_version():
    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"foundry {__version__}"


# --- runs list / runs show wiring (AC-4.3/AC-4.4) -------------------------------


def test_runs_list_prints_run_lines(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(
        RunEvent(run_id="r-a", card_id="c", stage=None, event="run_started", ts="t")
    )
    ledger.append(
        RunEvent(
            run_id="r-a", card_id="c", stage="build", event="stage_completed", ts="t",
            model="claude-sonnet-5", cost_usd=1.87,
        )
    )
    ledger.append(
        RunEvent(run_id="r-a", card_id="c", stage=None, event="run_completed", ts="t")
    )

    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "runs", "list"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "r-a run_completed $1.87"


# --- run --harness/--model/--effort wiring (AC-3.1) -----------------------


def test_run_parser_accepts_harness_model_effort_flags():
    from foundry.cli import build_parser

    args = build_parser().parse_args(
        ["run", "card-1", "--harness", "codex", "--model", "gpt-5.5", "--effort", "high"]
    )
    assert args.harness == "codex"
    assert args.model == "gpt-5.5"
    assert args.effort == "high"


def test_run_parser_flags_default_to_none():
    from foundry.cli import build_parser

    args = build_parser().parse_args(["run", "card-1"])
    assert args.harness is None
    assert args.model is None
    assert args.effort is None


def test_run_cli_threads_flags_into_run_command(monkeypatch, tmp_path):
    from foundry import cli, run_command

    captured = {}

    def fake_run(card_id, *, repo_root, path, adapter=None, ask=None, now=None,
                 interactive=False, interactive_run=None,
                 harness=None, model=None, effort=None):
        captured.update(harness=harness, model=model, effort=effort)

        class _Result:
            outcome = "completed"
            run_id = "r-1"
            stages_started = []

        return _Result()

    monkeypatch.setattr(run_command, "run", fake_run)
    monkeypatch.chdir(tmp_path)
    args = cli.build_parser().parse_args(
        ["run", "card-1", "--harness", "codex", "--model", "gpt-5.5", "--effort", "high"]
    )
    rc = cli._run(args)

    assert rc == 0
    assert captured == {"harness": "codex", "model": "gpt-5.5", "effort": "high"}


def test_runs_show_unknown_id_exits_2_listing_known_ids(tmp_path):
    ledger = RunLedger(tmp_path)
    ledger.append(
        RunEvent(run_id="r-known", card_id="c", stage=None, event="run_started", ts="t")
    )
    ledger.append(
        RunEvent(run_id="r-known", card_id="c", stage=None, event="run_completed", ts="t")
    )

    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "runs", "show", "r-missing"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "r-known" in result.stderr
