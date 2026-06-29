#!/usr/bin/env python3
"""Unit tests for grade_debug.py — the debug-eval grader.

Discrimination is the point: a real lldb session that hits a breakpoint, inspects
state, and names the faulting line PASSES; a static-only run that guesses the right
line with no debugger evidence FAILS (exit 1); an empty answer-key is rejected
(exit 2). Pure stdlib; runs the grader as a subprocess so the CLI contract is tested.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GRADER = os.path.join(HERE, "grade_debug.py")

ANSWER = {
    "fixture": "debug",
    "bug": "heap out-of-bounds write (off-by-one)",
    "file": "buggy.c",
    "function": "sum_of_squares",
    "fault_lines": [10, 11],
    "localize_any": ["buf[i]", "i <= n", "out of bounds", "off-by-one"],
}

# A real lldb session: breakpoint hit, frame inspected, faulting line named.
DEBUGGER_USED = """\
$ lldb --batch -o 'br set -f buggy.c -l 11 -c i==n' -o run -o bt -o 'frame variable' -o quit -- /tmp/buggy
Process 5123 stopped
* thread #1, stop reason = breakpoint 1.1
    frame #0: sum_of_squares(n=8) at buggy.c:11
(lldb) bt
  * frame #0: sum_of_squares(n=8) at buggy.c:11
    frame #1: main at buggy.c:22
(lldb) frame variable
(int) i = 8
(int) n = 8
The breakpoint hit at buggy.c:11 with i == 8 == n, so buf[8] is written out of bounds.
"""

# A static-only run: correct line guessed, but no debugger ran.
STATIC_ONLY = """\
Reading evals/fixtures/debug/buggy.c, the loop on line 10 uses `i <= n`, an
off-by-one, so buf[i] at buggy.c:11 writes out of bounds. Fix: use `i < n`.
"""

# Ran the debugger and inspected state, but never localized the fault.
NO_LOCALIZE = """\
$ lldb --batch -o run -o bt -o 'frame variable' -- /tmp/buggy
Process 5123 stopped
* thread #1, stop reason = breakpoint 1.1
(lldb) frame variable
(int) x = 3
It stopped, but I'm not sure where the problem is.
"""


def run(answer, transcript):
    tmp = tempfile.mkdtemp()
    akp = os.path.join(tmp, "answer-key.json")
    with open(akp, "w", encoding="utf-8") as handle:
        json.dump(answer, handle)
    tp = os.path.join(tmp, "transcript.txt")
    with open(tp, "w", encoding="utf-8") as handle:
        handle.write(transcript)
    proc = subprocess.run(
        [sys.executable, GRADER, akp, tp], capture_output=True, text=True
    )
    records = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    return proc.returncode, records


def case_of(records):
    return [r for r in records if r["event"] == "eval_case"][0]


class GradeDebugTest(unittest.TestCase):
    def test_debugger_used_passes(self):
        code, records = run(ANSWER, DEBUGGER_USED)
        self.assertEqual(code, 0)
        case = case_of(records)
        self.assertEqual(case["verdict"], "pass")
        self.assertTrue(all(case["signals"].values()))

    def test_static_only_fails_despite_right_line(self):
        code, records = run(ANSWER, STATIC_ONLY)
        self.assertEqual(code, 1)
        case = case_of(records)
        self.assertEqual(case["verdict"], "fail")
        self.assertTrue(case["signals"]["localized"])  # it DID name the line
        self.assertFalse(case["signals"]["debugger_used"])  # but ran no debugger
        self.assertIn("breakpoint_hit", case["missing"])

    def test_debugger_used_but_not_localized_fails(self):
        code, records = run(ANSWER, NO_LOCALIZE)
        self.assertEqual(code, 1)
        case = case_of(records)
        self.assertEqual(case["verdict"], "fail")
        self.assertIn("localized", case["missing"])

    def test_empty_answer_key_rejected(self):
        code, _ = run({"file": "buggy.c"}, DEBUGGER_USED)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
