"""m003_harness_agnostic (conv 2→3): `.claude/rules/` → `rules/`, manifest under
`.foundry/`, recorded harness set. All primitives are deterministic; the harness set is
inferred from what the repo carries (playbook rule)."""

from __future__ import annotations

import json

from foundry.materializer.migrations import m003_harness_agnostic as m


def test_applies_on_claude_rules_layout(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    assert m.applies(repo) is True


def test_apply_moves_rules(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    assert (repo / "rules" / "spec-conventions.md").is_file()
    assert (repo / "rules" / "knowledge-conventions.md").is_file()
    assert not (repo / ".claude" / "rules").exists()


def test_apply_moves_manifest_under_foundry(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    assert (repo / ".foundry" / "manifest.json").is_file()
    assert not (repo / ".foundry-manifest.json").exists()


def test_apply_records_harness_set(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    manifest = json.loads((repo / ".foundry" / "manifest.json").read_text())
    assert manifest["conventionVersion"] == 3
    # A CLAUDE.md is present → claude-code inferred; no codex signal.
    assert manifest["harnesses"] == ["claude-code"]


def test_apply_rewrites_path_references(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    agents = (repo / "AGENTS.md").read_text()
    assert ".claude/rules/" not in agents
    assert "rules/" in agents


def test_applies_false_after_migration(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    assert m.applies(repo) is False


def test_rerun_is_no_op(tmp_path, harness_fixture):
    repo = harness_fixture(tmp_path / "r")
    m.apply(repo)
    before = json.loads((repo / ".foundry" / "manifest.json").read_text())
    m.apply(repo)
    after = json.loads((repo / ".foundry" / "manifest.json").read_text())
    assert before == after
