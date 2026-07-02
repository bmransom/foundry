"""Prose lint: port of `prose-lint.py`'s CHECK behavior (design D5) — a deterministic
banned-filler-phrase gate over context-resident prose.

`check()` walks `roadmap/specs/` and `knowledge/` (excluding `index.md`) and returns
`(ok, findings)`; no sys.exit, no argv parsing. Neither directory existing yet is not a
failure — the check skips with a note, same posture as board/knowledge.
"""

from __future__ import annotations

import re
from pathlib import Path

# Multi-word, objectively removable filler. Case-insensitive. Generic English only.
BANNED = [
    "very basically",
    "basically just",
    "needless to say",
    "it goes without saying",
    "for all intents and purposes",
    "as a matter of fact",
    "at the end of the day",
    "it could perhaps be considered",
]
PATTERNS = [(p, re.compile(r"\b" + re.escape(p) + r"\b", re.IGNORECASE)) for p in BANNED]

_SCAN_DIRS = ("roadmap/specs", "knowledge")


def _lint_text(lines: list[str]):
    """Yield (lineno, phrase) for each banned phrase, skipping fenced code blocks."""
    in_fence = False
    for i, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for phrase, rx in PATTERNS:
            if rx.search(line):
                yield i, phrase


def check(repo_root: Path | str) -> tuple[bool, list[str]]:
    """Lint every `*.md` under `roadmap/specs/` and `knowledge/` (except `index.md`).
    Returns (ok, findings) — findings are prefixed `prose:`.
    """
    repo_root = Path(repo_root)
    paths = sorted(
        p
        for base in _SCAN_DIRS
        for p in (repo_root / base).rglob("*.md")
        if p.name != "index.md"
    )
    if not paths:
        return True, ["prose: skipped (no roadmap/specs or knowledge markdown files)"]

    findings: list[str] = []
    for path in paths:
        lines = path.read_text(encoding="utf-8").split("\n")
        rel = path.relative_to(repo_root)
        for lineno, phrase in _lint_text(lines):
            findings.append(f"prose: {rel}:{lineno}: banned filler phrase {phrase!r}")
    return not findings, findings
