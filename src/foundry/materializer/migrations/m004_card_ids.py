"""Migration m004 — card ids (convention 3 → 4).

Ports the `card-ids` playbook. Every board card table gains a slug-safe `Id` first
column; each claimable card (Ready / In progress / Validating) gets an `Id` derived from
its Work title. Column insertion and the slug rule are deterministic; collisions resolve
by numeric suffix (`-2`, `-3`, …).

Idempotent: `applies` keys on a card-table header that still lacks an `Id` column (or a
manifest below convention 4); once every table carries `Id`, it no longer fires.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CONVENTION = 4
ID = "card-ids"
_BOARD_REL = "roadmap/ROADMAP.md"
_MANIFEST_REL = ".foundry/manifest.json"
_CLAIMABLE = {"ready", "in progress", "validating"}


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_card_header(line: str) -> bool:
    if not line.strip().startswith("|"):
        return False
    cells = [c.lower() for c in _cells(line)]
    return "work" in cells and "status" in cells and "id" not in cells


def _is_separator(line: str) -> bool:
    return line.strip().startswith("|") and set(line.strip()) <= set("|-: ")


def applies(repo_root: Path | str) -> bool:
    repo_root = Path(repo_root)
    board = repo_root / _BOARD_REL
    if board.is_file():
        if any(_is_card_header(ln) for ln in board.read_text(encoding="utf-8").splitlines()):
            return True
    manifest_path = repo_root / _MANIFEST_REL
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("conventionVersion", 0) < CONVENTION:
            return True
    return False


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug or not re.match(r"^[a-z0-9]", slug):
        slug = f"card-{slug}".strip("-") or "card"
    return slug


def apply(repo_root: Path | str) -> list[str]:
    repo_root = Path(repo_root)
    board = repo_root / _BOARD_REL
    if board.is_file():
        _add_id_column(board)
    _stamp_manifest(repo_root)
    return []


def _add_id_column(board: Path) -> None:
    lines = board.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    used: set[str] = set()
    i = 0
    while i < len(lines):
        line = lines[i]
        if _is_card_header(line):
            header_cells = _cells(line)
            status_idx = [c.lower() for c in header_cells].index("status")
            work_idx = [c.lower() for c in header_cells].index("work")
            nl = "\n" if line.endswith("\n") else ""
            out.append("| Id | " + " | ".join(header_cells) + " |" + nl)
            # separator: one `---` column per header cell, plus the new Id column
            if i + 1 < len(lines) and _is_separator(lines[i + 1]):
                snl = "\n" if lines[i + 1].endswith("\n") else ""
                out.append("|" + "---|" * (len(header_cells) + 1) + snl)
                i += 2
            else:
                i += 1
            # rows
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i]
                cells = _cells(row)
                status = cells[status_idx].lower() if status_idx < len(cells) else ""
                work = cells[work_idx] if work_idx < len(cells) else ""
                if status in _CLAIMABLE:
                    slug = _slugify(work)
                    unique = slug
                    n = 2
                    while unique in used:
                        unique = f"{slug}-{n}"
                        n += 1
                    used.add(unique)
                    id_cell = unique
                else:
                    id_cell = ""
                rnl = "\n" if row.endswith("\n") else ""
                out.append("| " + id_cell + " | " + " | ".join(cells) + " |" + rnl)
                i += 1
            continue
        out.append(line)
        i += 1
    board.write_text("".join(out), encoding="utf-8")


def _stamp_manifest(repo_root: Path) -> None:
    path = repo_root / _MANIFEST_REL
    if not path.is_file():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["conventionVersion"] = CONVENTION
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
