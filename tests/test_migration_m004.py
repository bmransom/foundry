"""m004_card_ids (conv 3→4): board gains a slug-safe `Id` column, filled on claimable
cards from the Work title. Column insertion is deterministic; slug derivation is the
mechanical rule the playbook states, with numeric-suffix collision handling."""

from __future__ import annotations

import json

from foundry.materializer.migrations import m004_card_ids as m


def test_applies_when_board_lacks_id_column(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    assert m.applies(repo) is True


def test_apply_inserts_id_column(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    board = (repo / "roadmap" / "ROADMAP.md").read_text()
    header = next(ln for ln in board.splitlines() if ln.startswith("| Work") or "Id" in ln)
    assert board.splitlines()[board.splitlines().index(header)].startswith("| Id |")


def test_apply_fills_claimable_card_ids(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    board = (repo / "roadmap" / "ROADMAP.md").read_text()
    # "Paste command" Ready → slug paste-command; the second (In progress) collides → -2.
    assert "| paste-command |" in board
    assert "| paste-command-2 |" in board


def test_apply_leaves_non_claimable_id_empty(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    board = (repo / "roadmap" / "ROADMAP.md").read_text()
    copy_row = next(ln for ln in board.splitlines() if "Copy command" in ln)
    # Backlog card keeps an empty Id cell.
    assert copy_row.startswith("|  |") or copy_row.startswith("| |")


def test_apply_stamps_convention_4(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    manifest = json.loads((repo / ".foundry" / "manifest.json").read_text())
    assert manifest["conventionVersion"] == 4


def test_applies_false_after_migration(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    assert m.applies(repo) is False


def test_rerun_is_no_op(tmp_path, card_ids_fixture):
    repo = card_ids_fixture(tmp_path / "r")
    m.apply(repo)
    before = (repo / "roadmap" / "ROADMAP.md").read_text()
    m.apply(repo)
    assert (repo / "roadmap" / "ROADMAP.md").read_text() == before
