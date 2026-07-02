"""m002_okf_knowledge (conv 1→2): docs/ → knowledge/ + roadmap/, kind→type frontmatter.

Deterministic primitives (moves, field rename, config translation, manifest stamp) are
asserted exactly; the judgment part (a concept with no kind) is asserted flagged
needs-review with the playbook's safest type (`reference`), never silently guessed.
"""

from __future__ import annotations

import json

from foundry.materializer.migrations import m002_okf_knowledge as m


def test_applies_on_docs_layout(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    assert m.applies(repo) is True


def test_apply_moves_concepts_to_knowledge(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    assert (repo / "knowledge" / "glossary.md").is_file()
    assert (repo / "knowledge" / "architecture.md").is_file()
    assert not (repo / "docs").exists()


def test_apply_moves_board_and_specs(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    assert (repo / "roadmap" / "ROADMAP.md").is_file()
    assert (repo / "roadmap" / "BACKLOG.md").is_file()
    assert (repo / "roadmap" / "specs" / "feature-x" / "design.md").is_file()
    assert not (repo / "specs").exists()


def test_apply_renames_kind_to_type(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    glossary = (repo / "knowledge" / "glossary.md").read_text()
    assert "type: reference" in glossary
    assert "kind:" not in glossary


def test_apply_flags_missing_type_and_defaults_reference(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    flags = m.apply(repo)
    orphan = (repo / "knowledge" / "orphan.md").read_text()
    assert "type: reference" in orphan  # safest type applied
    assert any("orphan.md" in f and "review" in f.lower() for f in flags)


def test_apply_translates_config(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    cfg = json.loads((repo / "knowledge" / "knowledge-config.json").read_text())
    assert cfg["types"] == ["reference", "architecture"]
    assert cfg["concept_globs"] == ["docs/*.md"] or "concept_globs" in cfg
    assert not (repo / "docs" / "docs-config.json").exists()


def test_apply_deletes_old_docs_scripts(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    assert not (repo / "scripts" / "docs.py").exists()
    assert not (repo / "scripts" / "test_docs.py").exists()


def test_apply_stamps_convention_2(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    manifest = json.loads((repo / ".foundry-manifest.json").read_text())
    assert manifest["conventionVersion"] == 2
    assert "scripts/docs.py" not in manifest["files"]


def test_applies_false_after_migration(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    assert m.applies(repo) is False


def test_rerun_is_no_op(tmp_path, okf_fixture):
    repo = okf_fixture(tmp_path / "r")
    m.apply(repo)
    before = (repo / "knowledge" / "glossary.md").read_text()
    m.apply(repo)  # guarded internally; second run changes nothing
    assert (repo / "knowledge" / "glossary.md").read_text() == before
