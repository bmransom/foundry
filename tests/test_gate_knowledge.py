"""Tests for foundry.gate.knowledge (T11): port of knowledge.py check's semantics,
parameterized by knowledge/knowledge-config.json (same as v1)."""

import json
from pathlib import Path

from foundry.gate import knowledge

CONFIG = {
    "index_title": "Fixture knowledge",
    "okf_version": "0.1",
    "types": ["reference", "architecture", "guide", "decision"],
    "lifecycles": ["current", "superseded", "historical"],
    "required_fields": ["title", "description", "type"],
    "concept_globs": ["knowledge/*.md", "knowledge/**/*.md"],
    "exclude_substrings": [],
    "exclude_prefixes": [],
    "reserved_files": ["knowledge/index.md", "knowledge/log.md"],
    "skill_ref_prefixes": [],
}


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_config(root: Path, config: dict = CONFIG) -> None:
    write(root / "knowledge" / "knowledge-config.json", json.dumps(config))


def concept(title="Term", description="A term.", type_="reference") -> str:
    return f"---\ntitle: {title}\ndescription: {description}\ntype: {type_}\n---\n\n# {title}\n"


def test_missing_config_skips_ok(tmp_path):
    ok, findings = knowledge.check(tmp_path)
    assert ok is True
    assert any("skipped" in f for f in findings)


def test_clean_concept_with_fresh_index_passes(tmp_path):
    write_config(tmp_path)
    write(tmp_path / "knowledge" / "glossary.md", concept())
    # Build the expected fresh index the same way the check does, so the fixture's
    # index.md matches (freshness is part of what "clean" means here).
    expected = knowledge._build_index(knowledge._curated(str(tmp_path), CONFIG), CONFIG)
    write(tmp_path / "knowledge" / "index.md", expected)

    ok, findings = knowledge.check(tmp_path)
    assert ok is True
    assert findings == []


def test_missing_frontmatter_fails(tmp_path):
    write_config(tmp_path)
    write(tmp_path / "knowledge" / "glossary.md", "# No frontmatter\n")
    ok, findings = knowledge.check(tmp_path)
    assert ok is False
    assert any("missing frontmatter block" in f for f in findings)


def test_invalid_type_fails(tmp_path):
    write_config(tmp_path)
    write(tmp_path / "knowledge" / "glossary.md", concept(type_="bogus"))
    ok, findings = knowledge.check(tmp_path)
    assert ok is False
    assert any("invalid type 'bogus'" in f for f in findings)


def test_missing_required_field_fails(tmp_path):
    write_config(tmp_path)
    write(
        tmp_path / "knowledge" / "glossary.md",
        "---\ntitle: Term\ntype: reference\n---\n\n# Term\n",
    )
    ok, findings = knowledge.check(tmp_path)
    assert ok is False
    assert any("missing required field 'description'" in f for f in findings)


def test_stale_index_fails(tmp_path):
    write_config(tmp_path)
    write(tmp_path / "knowledge" / "glossary.md", concept())
    write(tmp_path / "knowledge" / "index.md", "stale content\n")
    ok, findings = knowledge.check(tmp_path)
    assert ok is False
    assert any("index.md is stale" in f for f in findings)


def test_reserved_files_are_not_validated(tmp_path):
    write_config(tmp_path)
    write(tmp_path / "knowledge" / "log.md", "not frontmatter at all\n")
    expected = knowledge._build_index(knowledge._curated(str(tmp_path), CONFIG), CONFIG)
    write(tmp_path / "knowledge" / "index.md", expected)
    ok, findings = knowledge.check(tmp_path)
    assert ok is True
    assert findings == []
