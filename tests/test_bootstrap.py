"""`foundry bootstrap` (T15, US-7 AC-7.1/AC-7.2, US-2 AC-2.4).

Answers-as-data intake, deterministic + idempotent materialize, manifest stamp, and the
gate-suite verify step. The interview seam is exercised with a fake adapter runner (no
live harness call). Smoke of the CLI wiring lives in test_cli.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tomllib
from pathlib import Path

import pytest

from foundry import __version__
from foundry.adapters import load as load_adapter
from foundry.config import Route
from foundry.materializer import bootstrap as b


ANSWERS = {
    "repo_name": "widgetworks",
    "description": "A service that assembles widgets.",
    "harnesses": ["claude-code", "codex"],
    "vocabulary": ["Widget", "Assembly"],
    "gate_test": "pytest -q",
    "gate_commands": ["scripts/check-heavy.sh"],
    "repo_url": "https://example.test/widgetworks",
}


def _answers(**overrides) -> b.Answers:
    data = {**ANSWERS, **overrides}
    return b.Answers.from_dict(data)


def _tree_snapshot(root: Path) -> dict[str, tuple[str, float]]:
    out: dict[str, tuple[str, float]] = {}
    for p in sorted(root.rglob("*")):
        if p.is_symlink():
            out[str(p.relative_to(root))] = ("symlink:" + os.readlink(p), 0.0)
        elif p.is_file():
            out[str(p.relative_to(root))] = (
                hashlib.sha256(p.read_bytes()).hexdigest(),
                p.stat().st_mtime,
            )
    return out


# --- Answers as data (AC-7.2) ---------------------------------------------------------


def test_answers_from_json_file(tmp_path):
    path = tmp_path / "answers.json"
    path.write_text(json.dumps(ANSWERS), encoding="utf-8")
    answers = b.Answers.from_json_file(path)
    assert answers.repo_name == "widgetworks"
    assert answers.harnesses == ("claude-code", "codex")
    assert answers.gate_test == "pytest -q"
    assert answers.gate_commands == ("scripts/check-heavy.sh",)


def test_default_pin_aligns_with_version():
    # doctor's config check compares pin == __version__ verbatim; default must match so a
    # freshly bootstrapped repo is doctor-clean.
    assert b.Answers.from_dict({"repo_name": "x"}).pin == __version__


# --- Deterministic materialize (AC-7.1) -----------------------------------------------


def test_verbatim_copied_byte_exact_with_exec_bits(tmp_path):
    b.materialize(tmp_path, _answers())
    src = b.verbatim_root()
    board = tmp_path / "scripts" / "board.sh"
    assert board.read_bytes() == (src / "scripts" / "board.sh").read_bytes()
    assert os.access(board, os.X_OK)
    # A non-executable verbatim file stays non-executable.
    pkg = tmp_path / "knowledge" / "package.json"
    assert pkg.read_bytes() == (src / "knowledge" / "package.json").read_bytes()
    assert not (pkg.stat().st_mode & stat.S_IXUSR)


def test_pre_push_is_pinned_not_verbatim(tmp_path):
    b.materialize(tmp_path, _answers())
    pre_push = tmp_path / ".githooks" / "pre-push"
    content = pre_push.read_text(encoding="utf-8")
    assert 'uvx --from "git+https://example.test/widgetworks@' in content
    assert "foundry gate" in content
    assert "check-fast" not in content
    assert os.access(pre_push, os.X_OK)


def test_manifest_stamped(tmp_path):
    b.materialize(tmp_path, _answers())
    manifest = json.loads((tmp_path / ".foundry" / "manifest.json").read_text())
    assert manifest["conventionVersion"] == 5
    assert manifest["harnesses"] == ["claude-code", "codex"]
    entry = manifest["files"]["scripts/board.sh"]
    assert entry["template"] == "board"
    assert entry["version"] == 1
    assert entry["sha256"] == hashlib.sha256(
        (tmp_path / "scripts" / "board.sh").read_bytes()
    ).hexdigest()
    pre_push_sha = hashlib.sha256((tmp_path / ".githooks" / "pre-push").read_bytes()).hexdigest()
    assert manifest["files"][".githooks/pre-push"]["sha256"] == pre_push_sha


def test_claude_md_symlink_when_claude_code(tmp_path):
    b.materialize(tmp_path, _answers(harnesses=["claude-code", "codex"]))
    claude_md = tmp_path / "CLAUDE.md"
    assert claude_md.is_symlink()
    assert os.readlink(claude_md) == "AGENTS.md"


def test_no_claude_md_when_codex_only(tmp_path):
    b.materialize(tmp_path, _answers(harnesses=["codex"]))
    assert not (tmp_path / "CLAUDE.md").exists()
    assert (tmp_path / "AGENTS.md").is_file()


def test_config_toml_written(tmp_path):
    b.materialize(tmp_path, _answers())
    config = tomllib.loads((tmp_path / ".foundry" / "config.toml").read_text())
    assert config["foundry"]["pin"] == __version__
    assert config["foundry"]["repo_url"] == "https://example.test/widgetworks"
    assert config["gate"]["test"] == "pytest -q"
    assert config["gate"]["commands"] == ["scripts/check-heavy.sh"]


def test_agents_md_has_sections_and_gate_command(tmp_path):
    b.materialize(tmp_path, _answers())
    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Commands" in agents
    assert "## Boundaries" in agents
    assert "## Task tracking" in agents
    assert "pytest -q" in agents
    assert "scripts/check-heavy.sh" in agents


def test_site_json_filled_from_answers(tmp_path):
    b.materialize(tmp_path, _answers())
    site = json.loads((tmp_path / "knowledge" / ".vitepress" / "site.json").read_text())
    assert site["title"] == "widgetworks"
    assert site["description"] == "A service that assembles widgets."


# --- Idempotency (AC-7.1) -------------------------------------------------------------


def test_second_run_over_pristine_writes_nothing(tmp_path):
    b.materialize(tmp_path, _answers())
    before = _tree_snapshot(tmp_path)
    result = b.materialize(tmp_path, _answers())
    after = _tree_snapshot(tmp_path)
    assert result.written == []
    assert before == after


def test_existing_differing_file_is_skipped_not_overwritten(tmp_path):
    target = tmp_path / "scripts" / "board.sh"
    target.parent.mkdir(parents=True)
    target.write_text("# my own board script\n", encoding="utf-8")
    result = b.materialize(tmp_path, _answers())
    assert target.read_text() == "# my own board script\n"
    assert "scripts/board.sh" in result.skipped


# --- Verify step ----------------------------------------------------------------------


def test_bootstrap_verify_ends_gate_pass(tmp_path):
    answers = _answers(gate_test=None, gate_commands=[])
    ok, lines = b.bootstrap(tmp_path, answers)
    assert lines[-1] == "gate: PASS"
    assert ok is True


# --- Interview seam (AC-7.2) with a fake adapter runner --------------------------------


def _fake_stream_json(reply_text: str) -> str:
    event = {
        "type": "result",
        "result": reply_text,
        "usage": {"input_tokens": 10, "output_tokens": 5},
    }
    return json.dumps(event) + "\n"


def test_interview_parses_answers_block(tmp_path):
    adapter = load_adapter("claude-code")
    reply = (
        "Here are the answers.\n\n```json\n"
        + json.dumps(ANSWERS)
        + "\n```\nDone.\n"
    )
    captured = {}

    def fake_run(argv, workspace, stdin=None):
        captured["argv"] = argv
        return _fake_stream_json(reply)

    answers = b.interview(
        adapter, Route("claude-code", "claude-opus-4-8"), str(tmp_path), run=fake_run
    )
    assert answers.repo_name == "widgetworks"
    assert answers.harnesses == ("claude-code", "codex")
    # The seam really invoked the harness command template.
    assert captured["argv"][0] == "claude"


def test_interview_raises_on_missing_answers_block(tmp_path):
    adapter = load_adapter("claude-code")

    def fake_run(argv, workspace, stdin=None):
        return _fake_stream_json("I could not produce answers.")

    with pytest.raises(b.BootstrapError):
        b.interview(
            adapter, Route("claude-code", "claude-opus-4-8"), str(tmp_path), run=fake_run
        )
