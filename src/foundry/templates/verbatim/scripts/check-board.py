#!/usr/bin/env python3
# foundry-template: check-board v2
# foundry-gate-tool: python3 scripts/check-board.py
"""Lint the ROADMAP board: card ids must be unique, slug-safe, and present on claimable cards.

Usage: check-board.py [roadmap-path]   (default: roadmap/ROADMAP.md beside this script's repo)

The board is one or more Markdown tables whose header names `Id`, `Work`, and `Status`.
This lint fails (exit 1) on any of:

  - a card table with no `Id` column,
  - a duplicate id (across all tables),
  - an id that is not slug-safe (^[a-z0-9][a-z0-9-]*$),
  - a claimable card (Status starts with Ready / In progress / Validating) with an empty id.

Empty ids are allowed on non-claimable cards (Done, Backlog, Planned, …) — presence is
scoped to where claiming happens. Pure stdlib; mirrors knowledge.py.
"""

import os
import re
import sys

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CLAIMABLE = ("ready", "in progress", "validating")


def split_row(line):
    """`| a | b | c |` -> ['a', 'b', 'c']; None when the line is not a table row."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [cell.strip() for cell in s.strip("|").split("|")]


def is_separator(line):
    s = line.strip()
    return s.startswith("|") and set(s) <= set("|-: ")


def is_card_header(row):
    lowered = [c.lower() for c in row]
    return "work" in lowered and "status" in lowered


def find_tables(lines):
    """Yield (header_row, [data_row, ...]) for each card table."""
    i, n = 0, len(lines)
    while i < n:
        row = split_row(lines[i])
        if row and not is_separator(lines[i]) and is_card_header(row):
            data = []
            j = i + 1
            if j < n and is_separator(lines[j]):
                j += 1
                while j < n:
                    if is_separator(lines[j]):
                        break
                    cells = split_row(lines[j])
                    if cells is None:
                        break
                    data.append(cells)
                    j += 1
            yield row, data
            i = j
        else:
            i += 1


def claimable(status):
    norm = status.lstrip("* ").lower()
    return any(norm.startswith(word) for word in CLAIMABLE)


def check(path):
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")

    violations = []
    seen = {}
    cards = ids = 0

    tables = list(find_tables(lines))
    if not tables:
        violations.append("no card tables found")

    for header, rows in tables:
        lowered = [c.lower() for c in header]
        if "id" not in lowered:
            violations.append(f"card table [{' | '.join(header)}] has no Id column")
            continue
        i_id, i_status = lowered.index("id"), lowered.index("status")
        i_work = lowered.index("work")
        for row in rows:
            if len(row) != len(header):
                violations.append(f"malformed row ({len(row)} cells, want {len(header)}): {row[:1]}")
                continue
            cards += 1
            cid, work = row[i_id], row[i_work][:48]
            if not cid:
                if claimable(row[i_status]):
                    violations.append(f"claimable card missing Id: {work!r}")
                continue
            ids += 1
            if not SLUG.match(cid):
                violations.append(f"Id not slug-safe: {cid!r} ({work!r})")
            if cid in seen:
                violations.append(f"duplicate Id: {cid!r}")
            seen[cid] = True

    for v in violations:
        print(f"board: {v}")
    if violations:
        print(f"board: FAIL ({len(violations)} issue(s))")
        return 1
    print(f"board: OK ({cards} cards, {ids} ids)")
    return 0


def main(argv):
    if len(argv) > 1:
        path = argv[1]
    else:
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(repo, "roadmap", "ROADMAP.md")
    if not os.path.isfile(path):
        print(f"board: ROADMAP not found: {path}", file=sys.stderr)
        return 2
    return check(path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
