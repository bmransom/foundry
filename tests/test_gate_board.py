"""Tests for foundry.gate.board (T11): port of check-board.py's CHECK behavior."""

from pathlib import Path

from foundry.gate import board


def write_board(root: Path, text: str) -> None:
    (root / "roadmap").mkdir(parents=True, exist_ok=True)
    (root / "roadmap" / "ROADMAP.md").write_text(text, encoding="utf-8")


CLEAN = """# Roadmap

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| wclip-paste | Paste command | Ready | `roadmap/specs/wclip-paste/` | — |
| wclip-copy | Copy command | Done | `roadmap/specs/wclip-copy/` | — |
"""


def test_missing_roadmap_skips_ok(tmp_path):
    ok, findings = board.check(tmp_path)
    assert ok is True
    assert any("skipped" in f for f in findings)


def test_clean_board_passes(tmp_path):
    write_board(tmp_path, CLEAN)
    ok, findings = board.check(tmp_path)
    assert ok is True
    assert findings == []


def test_claimable_card_missing_id_fails(tmp_path):
    text = """# Roadmap

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | New feature | Ready | `roadmap/specs/new-feature/` | — |
"""
    write_board(tmp_path, text)
    ok, findings = board.check(tmp_path)
    assert ok is False
    assert any("claimable card missing Id" in f for f in findings)


def test_non_claimable_card_missing_id_passes(tmp_path):
    text = """# Roadmap

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | Someday feature | Backlog | `roadmap/specs/someday/` | — |
"""
    write_board(tmp_path, text)
    ok, findings = board.check(tmp_path)
    assert ok is True
    assert findings == []


def test_duplicate_id_fails(tmp_path):
    text = """# Roadmap

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| dupe-id | First | Ready | `roadmap/specs/dupe-id/` | — |
| dupe-id | Second | Ready | `roadmap/specs/dupe-id/` | — |
"""
    write_board(tmp_path, text)
    ok, findings = board.check(tmp_path)
    assert ok is False
    assert any("duplicate Id" in f for f in findings)


def test_non_slug_id_fails(tmp_path):
    text = """# Roadmap

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| Not_Slug! | Weird id | Ready | `roadmap/specs/weird/` | — |
"""
    write_board(tmp_path, text)
    ok, findings = board.check(tmp_path)
    assert ok is False
    assert any("not slug-safe" in f for f in findings)


def test_table_without_id_column_fails(tmp_path):
    text = """# Roadmap

| Work | Status |
|---|---|
| Some work | Ready |
"""
    write_board(tmp_path, text)
    ok, findings = board.check(tmp_path)
    assert ok is False
    assert any("no Id column" in f for f in findings)


def test_no_card_tables_fails(tmp_path):
    write_board(tmp_path, "# Roadmap\n\nNo tables here.\n")
    ok, findings = board.check(tmp_path)
    assert ok is False
    assert any("no card tables found" in f for f in findings)
