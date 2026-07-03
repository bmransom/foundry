"""Tests for foundry.board (T7): the ROADMAP card-table parser and card resolution.

Covers multi-epic parsing, backtick-stripped spec paths, skipping blank-Id rows,
and unknown-id errors that list near matches (difflib) — AC-1.1.
"""

import pytest

from foundry.board import BoardError, Card, parse_board, resolve_card

BOARD = """# Roadmap

## Board conventions

Prose here, not a table row.

### Epic A

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | an unclaimed row with no id | Backlog | spec to write | — |
| alpha | First card | Ready | `roadmap/specs/alpha/` | — |

### Epic B

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| beta-two | Second card | In progress | `roadmap/specs/beta/` | alpha |
"""


def test_parse_board_reads_cards_across_epics():
    cards = parse_board(BOARD)
    ids = [c.id for c in cards]
    assert ids == ["alpha", "beta-two"]  # blank-id row skipped


def test_parse_board_extracts_fields_and_strips_backticks():
    cards = {c.id: c for c in parse_board(BOARD)}
    assert cards["alpha"].status == "Ready"
    assert cards["alpha"].spec == "roadmap/specs/alpha/"
    assert cards["beta-two"].status == "In progress"
    assert cards["beta-two"].depends_on == "alpha"


def test_resolve_card_by_id(tmp_path):
    (tmp_path / "roadmap").mkdir()
    (tmp_path / "roadmap" / "ROADMAP.md").write_text(BOARD)
    card = resolve_card(tmp_path, "beta-two")
    assert isinstance(card, Card)
    assert card.id == "beta-two"
    assert card.spec == "roadmap/specs/beta/"


def test_resolve_unknown_card_lists_near_matches(tmp_path):
    (tmp_path / "roadmap").mkdir()
    (tmp_path / "roadmap" / "ROADMAP.md").write_text(BOARD)
    with pytest.raises(BoardError) as excinfo:
        resolve_card(tmp_path, "beta-tow")
    message = str(excinfo.value)
    assert "beta-tow" in message
    assert "beta-two" in message  # difflib near match


def test_resolve_missing_board_raises(tmp_path):
    with pytest.raises(BoardError):
        resolve_card(tmp_path, "alpha")


# --- GFM escaped pipes (board-pipe-escapes) -----------------------------------


def test_escaped_pipes_stay_inside_their_cell():
    # GFM: `\|` is a literal pipe, not a cell delimiter — octant's board carried
    # math like `|x|` written as `\|x\|` and the parser split the row apart.
    board = (
        "| Id | Work | Status | Spec | Depends on |\n"
        "|---|---|---|---|---|\n"
        "| tol-honesty | scaled tolerance: `\\|d_j\\| <= tol / C_j` bound | Ready | `s/` | — |\n"
    )
    [card] = parse_board(board)
    assert card.id == "tol-honesty"
    assert "|d_j| <= tol / C_j" in card.work  # unescaped in the parsed cell
    assert card.status == "Ready"
