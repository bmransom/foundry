"""Tests for foundry.doctor (T12, AC-6.1/AC-6.2): one fixture per defect, each
producing exactly its finding; a clean fixture passes; exit codes plumb through
`foundry doctor`.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from foundry import __version__
from foundry import doctor

BROKEN_BOARD = (
    "# Fixture Roadmap\n\n"
    "| Id | Work | Status | Spec | Depends on |\n"
    "|---|---|---|---|---|\n"
    "|  | New feature | Ready | `roadmap/specs/new-feature/` | — |\n"
)

CHECK_FAST_PRE_PUSH = (
    "#!/usr/bin/env bash\n"
    'exec "$(git rev-parse --show-toplevel)/scripts/check-fast.sh"\n'
)

NEITHER_PRE_PUSH = "#!/usr/bin/env bash\necho hi\n"


def _findings(lines: list[str]) -> list[str]:
    """Lines that carry a fix (real findings), excluding notes and the summary."""
    return [line for line in lines if " — fix: " in line]


@pytest.fixture(autouse=True)
def _harnesses_available(monkeypatch):
    """Every doctor test isolates one defect at a time; harness availability is
    faked on unless a test explicitly overrides it (the adapters-unavailable test).
    """
    monkeypatch.setattr("shutil.which", lambda cmd: f"/usr/bin/{cmd}")


# --- clean fixture ----------------------------------------------------------


def test_clean_fixture_passes(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path)
    ok, lines = doctor.run(repo)

    assert ok is True
    assert _findings(lines) == []
    assert lines[-1] == f"doctor: OK ({len(doctor.CHECK_NAMES)} checks)"


# --- config -------------------------------------------------------------------


def test_malformed_config_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, config_malformed=True)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "config" in findings[0] and "malformed" in findings[0]


def test_pin_mismatch_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, pin="v0.0.1")
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "config" in findings[0]
    assert "v0.0.1" in findings[0] and __version__ in findings[0]


def test_absent_pin_is_a_note_not_a_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, pin=None)
    ok, lines = doctor.run(repo)

    assert ok is True
    assert _findings(lines) == []
    assert any("no [foundry].pin set" in line for line in lines)


# --- manifest -------------------------------------------------------------------


def test_manifest_hash_mismatch_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, manifest_hash_defect=True)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "manifest" in findings[0] and "sha256 mismatch" in findings[0]


def test_missing_manifest_is_a_skip_note(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, manifest_present=False)
    ok, lines = doctor.run(repo)

    assert ok is True
    assert _findings(lines) == []
    assert any("pre-bootstrap repo" in line for line in lines)


# --- adapters -------------------------------------------------------------------


def test_routed_harness_missing_from_manifest_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, manifest_harnesses=[])
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "adapters" in findings[0] and "manifest's harnesses set" in findings[0]


def test_adapter_command_not_on_path_is_one_finding(tmp_path, doctor_fixture, monkeypatch):
    repo = doctor_fixture(tmp_path)
    monkeypatch.setattr("shutil.which", lambda cmd: None if cmd == "claude" else f"/usr/bin/{cmd}")

    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "adapters" in findings[0] and "not found on PATH" in findings[0]


# --- hooks -------------------------------------------------------------------


def test_hooks_path_unset_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, hooks_path_set=False)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "hooks" in findings[0] and "core.hooksPath" in findings[0]


def test_pre_push_invoking_neither_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, pre_push_text=NEITHER_PRE_PUSH)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "hooks" in findings[0] and "invokes neither" in findings[0]


def test_pre_push_invoking_check_fast_is_a_tolerated_note(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, pre_push_text=CHECK_FAST_PRE_PUSH)
    ok, lines = doctor.run(repo)

    assert ok is True
    assert _findings(lines) == []
    assert any("check-fast.sh" in line and "tolerated" in line for line in lines)


def test_missing_pre_push_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, pre_push_text=None)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "hooks" in findings[0] and "pre-push is missing" in findings[0]


# --- board -------------------------------------------------------------------


def test_board_defect_is_one_finding(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, board_text=BROKEN_BOARD)
    ok, lines = doctor.run(repo)

    assert ok is False
    findings = _findings(lines)
    assert len(findings) == 1
    assert "board" in findings[0] and "claimable card missing Id" in findings[0]


# --- doctor: <n> finding(s) summary -------------------------------------------


def test_finding_summary_counts_only_failures(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, board_text=BROKEN_BOARD, pin="v0.0.1")
    ok, lines = doctor.run(repo)

    assert ok is False
    assert lines[-1] == "doctor: 2 finding(s)"


# --- CLI wiring / exit codes ---------------------------------------------------


def test_doctor_is_not_a_stub_subcommand():
    from foundry.cli import STUB_SUBCOMMANDS

    assert "doctor" not in STUB_SUBCOMMANDS


def test_doctor_cli_exits_zero_on_clean_fixture(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path)
    fake_bin = tmp_path.parent / "fake-bin"
    fake_bin.mkdir(exist_ok=True)
    for name in ("claude", "codex"):
        stub = fake_bin / name
        stub.write_text("#!/bin/sh\nexit 0\n")
        stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"}

    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "doctor"],
        cwd=str(repo), capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0
    assert result.stdout.rstrip("\n").splitlines()[-1] == f"doctor: OK ({len(doctor.CHECK_NAMES)} checks)"


def test_doctor_cli_exits_nonzero_on_defect_fixture(tmp_path, doctor_fixture):
    repo = doctor_fixture(tmp_path, board_text=BROKEN_BOARD)
    result = subprocess.run(
        [sys.executable, "-m", "foundry.cli", "doctor"],
        cwd=str(repo), capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "finding(s)" in result.stdout.rstrip("\n").splitlines()[-1]


def test_config_pin_tolerates_v_prefix(doctor_fixture, tmp_path):
    repo = doctor_fixture(tmp_path, pin="v" + __version__)
    ok, lines = doctor.run(repo)
    assert ok, lines
    assert not [l for l in lines if "pin" in l and "fix:" in l]
