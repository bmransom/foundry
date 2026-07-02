"""Tests for foundry.gate.prose (T11): port of prose-lint.py's CHECK behavior."""

from pathlib import Path

from foundry.gate import prose


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_no_specs_or_knowledge_dirs_skips_ok(tmp_path):
    ok, findings = prose.check(tmp_path)
    assert ok is True
    assert any("skipped" in f for f in findings)


def test_clean_prose_passes(tmp_path):
    write(tmp_path / "roadmap" / "specs" / "demo" / "requirements.md", "# Demo\n\nClean prose.\n")
    ok, findings = prose.check(tmp_path)
    assert ok is True
    assert findings == []


def test_banned_phrase_fails(tmp_path):
    write(
        tmp_path / "roadmap" / "specs" / "demo" / "design.md",
        "# Demo\n\nNeedless to say, this works.\n",
    )
    ok, findings = prose.check(tmp_path)
    assert ok is False
    assert any("needless to say" in f for f in findings)


def test_banned_phrase_in_fenced_code_block_is_skipped(tmp_path):
    write(
        tmp_path / "knowledge" / "example.md",
        "# Example\n\n```\nNeedless to say, this is code.\n```\n",
    )
    ok, findings = prose.check(tmp_path)
    assert ok is True
    assert findings == []


def test_index_md_is_excluded(tmp_path):
    write(tmp_path / "knowledge" / "index.md", "Needless to say, this is the index.\n")
    write(tmp_path / "knowledge" / "glossary.md", "# Glossary\n\nClean.\n")
    ok, findings = prose.check(tmp_path)
    assert ok is True
    assert not any("needless to say" in f for f in findings)
