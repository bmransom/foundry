"""Tests for `foundry gate` wiring (T11): moved out of STUB_SUBCOMMANDS, exit code
from the suite, `gate: PASS`/`gate: FAIL` printed as the last line."""

import subprocess
import sys


def test_gate_is_not_a_stub_subcommand():
    from foundry.cli import STUB_SUBCOMMANDS

    assert "gate" not in STUB_SUBCOMMANDS


def test_gate_passes_on_a_clean_fixture_and_prints_pass_last(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "gate"],
        cwd=str(repo), capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert result.stdout.rstrip("\n").splitlines()[-1] == "gate: PASS"


def test_gate_fails_on_a_defect_fixture_and_exits_nonzero(tmp_path, gate_fixture):
    repo = gate_fixture(tmp_path, board_defect=True)
    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "gate"],
        cwd=str(repo), capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert result.stdout.rstrip("\n").splitlines()[-1] == "gate: FAIL"
