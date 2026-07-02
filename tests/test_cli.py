"""Tests for foundry.cli."""

import subprocess
import sys

from foundry import __version__


def test_version():
    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"foundry {__version__}"
