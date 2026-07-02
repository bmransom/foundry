"""Gate-suite fixture builder (T11): a minimal repo tree for exercising
`foundry.gate.suite` end-to-end. Distinct from the git-backed `repo_factory`
(tests/fixtures/repos/factory.py) — gate checks are pure filesystem, no git needed.
"""

from __future__ import annotations

import json
from pathlib import Path

from foundry.gate import knowledge as gate_knowledge

_KNOWLEDGE_CONFIG = {
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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_gate_fixture(
    root: Path,
    *,
    board_defect: bool = False,
    prose_defect: bool = False,
    knowledge_defect: bool = False,
    gate_command: str | None = None,
) -> Path:
    """Build a minimal repo tree with a clean board card, spec file, and knowledge
    concept, optionally seeding one defect per check — so a discrimination test can
    assert that check FAILs while the others stay clean. `gate_command` seeds a
    `[gate].commands` entry (a shell-safe argv string); pass a command that exits
    non-zero to make the suite's command step fail.
    """
    root = Path(root)

    card_row = (
        "|  | New feature | Ready | `roadmap/specs/new-feature/` | — |\n"
        if board_defect
        else "| clean-card | Clean card | Ready | `roadmap/specs/clean-card/` | — |\n"
    )
    _write(
        root / "roadmap" / "ROADMAP.md",
        "# Fixture Roadmap\n\n"
        "| Id | Work | Status | Spec | Depends on |\n"
        "|---|---|---|---|---|\n" + card_row,
    )

    spec_body = (
        "# Demo\n\nNeedless to say, this works.\n"
        if prose_defect
        else "# Demo\n\nClean prose.\n"
    )
    _write(root / "roadmap" / "specs" / "demo" / "design.md", spec_body)

    concept_type = "bogus" if knowledge_defect else "reference"
    _write(
        root / "knowledge" / "glossary.md",
        f"---\ntitle: Term\ndescription: A term.\ntype: {concept_type}\n---\n\n# Term\n",
    )
    _write(root / "knowledge" / "knowledge-config.json", json.dumps(_KNOWLEDGE_CONFIG))
    # A fresh index for whatever concept set exists so a knowledge-type defect is the
    # only knowledge finding (not conflated with unrelated index staleness).
    expected_index = gate_knowledge._build_index(
        gate_knowledge._curated(str(root), _KNOWLEDGE_CONFIG), _KNOWLEDGE_CONFIG
    )
    _write(root / "knowledge" / "index.md", expected_index)

    commands = json.dumps([gate_command]) if gate_command else "[]"
    _write(root / ".foundry" / "config.toml", f"[gate]\ncommands = {commands}\n")

    return root
