"""Parity test (T11, tasks.md): the ported gate checks must agree with the v1
scripts' verdicts on this repo's own tree — same pass/fail, not the same wording.

Discrimination lives in tests/test_gate_discrimination.py: each check must FAIL its
seeded defect, never green-ness alone (AC-8.2 / knowledge/coe-template posture).
"""

import subprocess
import sys
from pathlib import Path

from foundry.gate import board, knowledge, prose

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(argv: list[str]) -> int:
    return subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True, text=True).returncode


def test_board_check_agrees_with_v1_script():
    v1_ok = _run([sys.executable, "scripts/check-board.py"]) == 0
    ported_ok, _ = board.check(REPO_ROOT)
    assert ported_ok == v1_ok


def test_prose_check_agrees_with_v1_script():
    paths = sorted(
        str(p)
        for base in ("roadmap/specs", "knowledge")
        for p in (REPO_ROOT / base).rglob("*.md")
        if p.name != "index.md"
    )
    v1_ok = _run([sys.executable, "scripts/prose-lint.py", *paths]) == 0
    ported_ok, _ = prose.check(REPO_ROOT)
    assert ported_ok == v1_ok


def test_knowledge_check_agrees_with_v1_script():
    v1_ok = _run([sys.executable, "scripts/knowledge.py", "check"]) == 0
    ported_ok, _ = knowledge.check(REPO_ROOT)
    assert ported_ok == v1_ok
