"""Migration eval for m005_pinned_run (T13, AC-5.3): a conv-4 v1-layout fixture
migrates green and re-running `apply` is a byte-identical no-op.

Not a live-LLM eval — the migration is deterministic code, so this pytest fixture eval
is its discrimination surface: it asserts the config is written with the old gate command
preserved, the pre-push + CI rewritten to the pinned `uvx` command, the fully-owned gate
scripts deleted, knowledge.py kept, and the manifest restamped to conv 5.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from foundry import __version__
from foundry.materializer.migrations import m005_pinned_run as m

REPO_URL = "https://example.test/foundry"
PIN = "vtest-pin"


def _tree_hash(root: Path) -> dict[str, str]:
    """sha256 per tracked file (excluding .git), for a byte-identity no-op assertion."""
    out: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file() and ".git" not in p.parts:
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def test_applies_on_conv4_vendored_repo(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    assert m.applies(repo) is True


def test_apply_writes_config_preserving_old_gate_command(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)

    config = tomllib.loads((repo / ".foundry" / "config.toml").read_text())
    assert config["foundry"]["pin"] == PIN
    assert config["foundry"]["repo_url"] == REPO_URL
    # The old pre-push ran scripts/check-fast.sh — nothing is lost.
    assert config["gate"]["commands"] == ["scripts/check-fast.sh"]


def test_apply_rewrites_pre_push_to_pinned_command(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)

    pre_push = (repo / ".githooks" / "pre-push").read_text()
    assert f'uvx --from "git+{REPO_URL}@{PIN}" foundry gate' in pre_push
    assert "check-fast.sh" not in pre_push


def test_apply_rewrites_ci_gate_step_only(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)

    ci = (repo / ".github" / "workflows" / "check-fast.yml").read_text()
    assert f'uvx --from "git+{REPO_URL}@{PIN}" foundry gate' in ci
    assert "run: scripts/check-fast.sh" not in ci
    # Other steps survive.
    assert "npm run build" in ci


def test_apply_deletes_owned_scripts_keeps_knowledge(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)

    for gone in (
        "scripts/check-board.py",
        "scripts/prose-lint.py",
        "scripts/test_check_board.py",
        "scripts/test_prose_lint.py",
    ):
        assert not (repo / gone).exists(), f"{gone} should be deleted"
    # knowledge.py stays: the suite ports only its `check`; list/index remain in use.
    assert (repo / "scripts" / "knowledge.py").exists()
    assert (repo / "scripts" / "check-fast.sh").exists()


def test_apply_updates_manifest(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)

    manifest = json.loads((repo / ".foundry" / "manifest.json").read_text())
    assert manifest["conventionVersion"] == 5
    assert "scripts/check-board.py" not in manifest["files"]
    assert "scripts/knowledge.py" in manifest["files"]
    # The pre-push hash tracks its rewritten content (doctor's manifest check stays green).
    pre_push_bytes = (repo / ".githooks" / "pre-push").read_bytes()
    assert manifest["files"][".githooks/pre-push"]["sha256"] == hashlib.sha256(
        pre_push_bytes
    ).hexdigest()


def test_applies_false_after_migration(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)
    assert m.applies(repo) is False


def test_rerun_is_byte_identical_no_op(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, pin=PIN, repo_url=REPO_URL)
    before = _tree_hash(repo)
    m.apply(repo, pin=PIN, repo_url=REPO_URL)
    after = _tree_hash(repo)
    assert before == after


def test_default_pin_is_version_prefixed_v(tmp_path, pinned_run_fixture):
    repo = pinned_run_fixture(tmp_path / "r")
    m.apply(repo, repo_url=REPO_URL)  # pin omitted -> default
    config = tomllib.loads((repo / ".foundry" / "config.toml").read_text())
    assert config["foundry"]["pin"] == "v" + __version__
