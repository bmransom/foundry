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
