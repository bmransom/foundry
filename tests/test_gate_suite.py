"""Tests for foundry.gate.suite (T11): board + prose + knowledge checks plus
[gate].commands; last line exactly `gate: PASS`/`gate: FAIL` (AC-5.2)."""

from pathlib import Path

from foundry.gate import suite


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_no_config_and_no_repo_files_passes_with_skip_notes(tmp_path):
    ok, lines = suite.run(tmp_path)
    assert ok is True
    assert lines[-1] == "gate: PASS"
    assert any("board" in line and "skipped" in line for line in lines)
    assert any("prose" in line and "skipped" in line for line in lines)
    assert any("knowledge" in line and "skipped" in line for line in lines)


def test_board_failure_fails_the_suite(tmp_path):
    write(
        tmp_path / "roadmap" / "ROADMAP.md",
        "# Roadmap\n\n"
        "| Id | Work | Status | Spec | Depends on |\n"
        "|---|---|---|---|---|\n"
        "|  | New feature | Ready | `roadmap/specs/new-feature/` | — |\n",
    )
    ok, lines = suite.run(tmp_path)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("claimable card missing Id" in line for line in lines)


def test_gate_commands_run_and_a_failing_one_fails_the_suite(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        '[gate]\ncommands = ["python3 -c \\"import sys; sys.exit(1)\\""]\n',
    )
    ok, lines = suite.run(tmp_path)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("command failed" in line for line in lines)


def test_gate_commands_all_passing_keeps_the_suite_green(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        '[gate]\ncommands = ["python3 -c \\"import sys; sys.exit(0)\\""]\n',
    )
    ok, lines = suite.run(tmp_path)
    assert ok is True
    assert lines[-1] == "gate: PASS"


def test_malformed_config_fails_the_suite_with_a_finding_instead_of_a_traceback(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        "[gate\ncommands = [\n",  # unterminated table header -> tomllib.TOMLDecodeError
    )
    ok, lines = suite.run(tmp_path)
    assert ok is False
    assert lines[-1] == "gate: FAIL"
    assert any("config" in line and "malformed" in line for line in lines)
