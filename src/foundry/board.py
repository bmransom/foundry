"""Board resolution (AC-1.1): parse roadmap/ROADMAP.md card tables and resolve a
card by Id.

A card is one table row `| Id | Work | Status | Spec | Depends on |` (the board
conventions in ROADMAP.md). Rows with a blank Id are unclaimable and skipped. An
unknown id raises BoardError listing near matches (difflib). Stdlib only.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from pathlib import Path

HEADER = ("Id", "Work", "Status", "Spec", "Depends on")


class BoardError(Exception):
    """The board is missing, or a card id does not resolve."""


@dataclass(frozen=True)
class Card:
    id: str
    work: str
    status: str
    spec: str
    depends_on: str


def _cells(line: str) -> list[str] | None:
    """Split a markdown table row into stripped cells, or None if not a table row."""
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    parts = stripped.split("|")
    # A leading and trailing '|' produce empty edge fields; drop them.
    return [p.strip() for p in parts[1:-1]]


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") and "-" in c for c in cells)


def parse_board(text: str) -> list[Card]:
    """Parse every `| Id | Work | Status | Spec | Depends on |` table across the board."""
    cards: list[Card] = []
    in_table = False
    for line in text.splitlines():
        cells = _cells(line)
        if cells is None:
            in_table = False
            continue
        if tuple(cells) == HEADER:
            in_table = True
            continue
        if not in_table:
            continue
        if _is_separator(cells):
            continue
        if len(cells) < 5:
            continue
        card_id = cells[0].strip("` ")
        if not card_id:
            continue  # unclaimable row
        cards.append(
            Card(
                id=card_id,
                work=cells[1],
                status=cells[2],
                spec=cells[3].strip("` "),
                depends_on=cells[4],
            )
        )
    return cards


def board_path(repo_root: Path | str) -> Path:
    return Path(repo_root) / "roadmap" / "ROADMAP.md"


def resolve_card(repo_root: Path | str, card_id: str) -> Card:
    """Resolve `card_id` against the repo's board; unknown id → BoardError with near matches."""
    path = board_path(repo_root)
    if not path.is_file():
        raise BoardError(f"no board at {path}")
    cards = {c.id: c for c in parse_board(path.read_text(encoding="utf-8"))}
    if card_id in cards:
        return cards[card_id]
    near = difflib.get_close_matches(card_id, list(cards), n=3)
    hint = f"; did you mean: {', '.join(near)}?" if near else ""
    raise BoardError(f"unknown card '{card_id}'{hint}")
