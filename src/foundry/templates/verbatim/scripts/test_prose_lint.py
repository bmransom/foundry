#!/usr/bin/env python3
# foundry-template: test-prose-lint v1
"""Discrimination tests for prose-lint.py: a banned filler phrase fails, clean prose passes."""

import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LINT = os.path.join(HERE, "prose-lint.py")

CLEAN = "# Title\n\nThis sentence is tight and makes a definite assertion.\n"
DIRTY = "# Title\n\nThis is, needless to say, a wordy sentence.\n"
FENCED = "# Title\n\n```\nneedless to say this is inside a code fence\n```\n\nClean prose.\n"


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
        handle.write(text)
        path = handle.name
    try:
        proc = subprocess.run([sys.executable, LINT, path], capture_output=True, text=True)
        return proc.returncode, proc.stdout
    finally:
        os.unlink(path)


class ProseLintTest(unittest.TestCase):
    def test_clean_passes(self):
        code, out = run(CLEAN)
        self.assertEqual(code, 0, out)
        self.assertIn("prose-lint: OK", out)

    def test_banned_phrase_fails(self):
        code, out = run(DIRTY)
        self.assertEqual(code, 1, out)
        self.assertIn("needless to say", out)

    def test_fenced_code_skipped(self):
        code, out = run(FENCED)
        self.assertEqual(code, 0, out)

    def test_v8_needless_qualifier_caught(self):
        # reviewer-eval V8 ("very basically") moved here: prose-lint owns objective filler.
        code, out = run("# T\n\nThis is very basically a restatement.\n")
        self.assertEqual(code, 1, out)
        self.assertIn("very basically", out)


if __name__ == "__main__":
    unittest.main()
