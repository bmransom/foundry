"""Pytest repo fixture factory (design §New vocabulary): a minimal git repo with a
ROADMAP card table and .foundry/config.toml, for the T7 run-command smoke tests.

Test-local only — never an eval target.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

_IDENTITY = ("-c", "user.email=test@foundry", "-c", "user.name=Foundry Test")


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=check, capture_output=True, text=True
    )


def _roadmap(cards: list[tuple[str, str]]) -> str:
    rows = "\n".join(
        f"| {card_id} | {work} | Ready | `roadmap/specs/{card_id}/` | — |"
        for card_id, work in cards
    )
    return (
        "# Fixture Roadmap\n\n"
        "## Status Dashboard\n\n"
        "### Epic 0 — fixture\n\n"
        "| Id | Work | Status | Spec | Depends on |\n"
        "|---|---|---|---|---|\n"
        f"{rows}\n"
    )


def _config(gate_test: str, gate_commands: list[str]) -> str:
    commands = ", ".join(f'"{c}"' for c in gate_commands)
    return (
        "[foundry]\n"
        'pin = "v2.0.0"\n\n'
        "[gate]\n"
        f'test = "{gate_test}"\n'
        f"commands = [{commands}]\n\n"
        "[autonomy]\n"
        'level = "autonomous"\n'
        'stop_point = "card"\n'
    )


def make_repo(
    root: Path,
    *,
    cards: list[tuple[str, str]] | None = None,
    default_branch: str = "main",
    gate_test: str = "true",
    gate_commands: list[str] | None = None,
) -> Path:
    """Build a git repo at `root` with a board card table and .foundry/config.toml,
    committed on `default_branch`. `cards` is a list of (id, work) pairs.
    """
    root = Path(root)
    cards = cards or [("wclip-paste", "Paste command")]
    gate_commands = gate_commands or []

    _git(root, "init", "-b", default_branch)

    (root / "roadmap").mkdir(parents=True, exist_ok=True)
    (root / "roadmap" / "ROADMAP.md").write_text(_roadmap(cards), encoding="utf-8")

    (root / ".foundry").mkdir(parents=True, exist_ok=True)
    (root / ".foundry" / "config.toml").write_text(
        _config(gate_test, gate_commands), encoding="utf-8"
    )

    _git(root, *_IDENTITY, "add", "-A")
    _git(root, *_IDENTITY, "commit", "-m", "init fixture repo")
    return root


def head_sha(root: Path, branch: str) -> str:
    return _git(root, "rev-parse", branch).stdout.strip()


def branch_exists(root: Path, branch: str) -> bool:
    return _git(root, "rev-parse", "--verify", "--quiet", branch, check=False).returncode == 0
