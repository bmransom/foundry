#!/usr/bin/env python3
# foundry-template: test-check-board v1
"""Unit tests for check-board.py — the board lint must discriminate.

Each test writes a synthetic ROADMAP to a tmp file and runs check-board.py as a
subprocess (the real CLI: argv, exit code, stdout). A clean board passes; each seeded
defect — duplicate id, claimable card missing an id, a non-slug-safe id, a missing Id
column — must make the lint exit non-zero. Pure stdlib.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LINT = Path(__file__).resolve().parent / "check-board.py"

VALID = """## Status Dashboard

### Epic A

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| a-one | First card | **In progress** — building | `spec/` | — |
| | Shipped card | Done — gate PASS | `spec/` | — |
| a-two | Third card | Validating — built | `spec/` | a-one |
| | Future card | Backlog | spec to write | — |
"""


def run(board):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "ROADMAP.md"
        path.write_text(board, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(LINT), str(path)],
            capture_output=True,
            text=True,
        )
    return proc.returncode, proc.stdout


class BoardLintTest(unittest.TestCase):
    def test_clean_board_passes(self):
        code, out = run(VALID)
        self.assertEqual(code, 0, out)
        self.assertIn("board: OK", out)
        # AC-1.5 also requires the success line to report the card and id counts.
        self.assertRegex(out, r"\d+ cards, \d+ ids")

    def test_blank_id_on_done_card_passes(self):
        # The VALID board has Done + Backlog rows with empty ids — must not fail.
        code, _ = run(VALID)
        self.assertEqual(code, 0)

    def test_duplicate_id_fails(self):
        board = VALID.replace("| a-two | Third card", "| a-one | Third card")
        code, out = run(board)
        self.assertEqual(code, 1, out)
        self.assertIn("duplicate Id", out)

    def test_claimable_missing_id_fails(self):
        board = VALID.replace("| a-one | First card", "|  | First card")
        code, out = run(board)
        self.assertEqual(code, 1, out)
        self.assertIn("missing Id", out)

    def test_non_slug_id_fails(self):
        board = VALID.replace("| a-one |", "| A One |")
        code, out = run(board)
        self.assertEqual(code, 1, out)
        self.assertIn("slug-safe", out)

    def test_missing_id_column_fails(self):
        board = """### Epic A

| Work | Status | Spec | Depends on |
|---|---|---|---|
| First card | In progress | `spec/` | — |
"""
        code, out = run(board)
        self.assertEqual(code, 1, out)
        self.assertIn("no Id column", out)


if __name__ == "__main__":
    unittest.main()
