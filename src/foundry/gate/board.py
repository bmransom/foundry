"""Board schema check: port of `check-board.py`'s CHECK behavior (design D5).

Card table shape (Id/Work/Status columns), duplicate/slug-safe Id, and Id required on
claimable cards (Ready / In progress / Validating status) — ported faithfully from the
v1 script. `check()` returns `(ok, findings)`; no sys.exit, no argv parsing. When
`roadmap/ROADMAP.md` is absent, the check skips (ok, with a note) rather than failing —
a repo without a board yet isn't a gate failure.
"""

from __future__ import annotations

import re
from pathlib import Path

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CLAIMABLE = ("ready", "in progress", "validating")


def _split_row(line: str) -> list[str] | None:
    """`| a | b | c |` -> ['a', 'b', 'c']; None when the line is not a table row."""
    s = line.strip()
    if not s.startswith("|"):
        return None
    return [cell.strip() for cell in s.strip("|").split("|")]


def _is_separator(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and set(s) <= set("|-: ")


def _is_card_header(row: list[str]) -> bool:
    lowered = [c.lower() for c in row]
    return "work" in lowered and "status" in lowered


def _find_tables(lines: list[str]):
    """Yield (header_row, [data_row, ...]) for each card table."""
    i, n = 0, len(lines)
    while i < n:
        row = _split_row(lines[i])
        if row and not _is_separator(lines[i]) and _is_card_header(row):
            data: list[list[str]] = []
            j = i + 1
            if j < n and _is_separator(lines[j]):
                j += 1
                while j < n:
                    if _is_separator(lines[j]):
                        break
                    cells = _split_row(lines[j])
                    if cells is None:
                        break
                    data.append(cells)
                    j += 1
            yield row, data
            i = j
        else:
            i += 1


def _claimable(status: str) -> bool:
    norm = status.lstrip("* ").lower()
    return any(norm.startswith(word) for word in CLAIMABLE)


def check(repo_root: Path | str) -> tuple[bool, list[str]]:
    """Lint `roadmap/ROADMAP.md`. Returns (ok, findings) — findings are prefixed
    `board:` for the gate suite's flat finding list.
    """
    path = Path(repo_root) / "roadmap" / "ROADMAP.md"
    if not path.is_file():
        return True, ["board: skipped (no roadmap/ROADMAP.md)"]

    lines = path.read_text(encoding="utf-8").split("\n")
    violations: list[str] = []
    seen: dict[str, bool] = {}

    tables = list(_find_tables(lines))
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
                violations.append(
                    f"malformed row ({len(row)} cells, want {len(header)}): {row[:1]}"
                )
                continue
            cid, work = row[i_id], row[i_work][:48]
            if not cid:
                if _claimable(row[i_status]):
                    violations.append(f"claimable card missing Id: {work!r}")
                continue
            if not SLUG.match(cid):
                violations.append(f"Id not slug-safe: {cid!r} ({work!r})")
            if cid in seen:
                violations.append(f"duplicate Id: {cid!r}")
            seen[cid] = True

    findings = [f"board: {v}" for v in violations]
    return not violations, findings
