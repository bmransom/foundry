"""Static checks for bootstrap fixture expectations.

The live bootstrap eval grades generated scratch repos by these JSON files. If
they drift behind the current convention, every live fixture can fail even when
the generated repo is correct.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

EXPECTATION_FILES = [
    ROOT / "evals" / "fixtures" / "python-service" / "expectations.json",
    ROOT / "evals" / "fixtures" / "rust-cli" / "expectations.json",
    ROOT / "evals" / "fixtures" / "ts-monorepo" / "expectations.json",
    ROOT / "evals" / "harness" / "wclip-smoke-expectations.json",
]


class BootstrapExpectationConventionTest(unittest.TestCase):
    def test_expectations_encode_convention_3_layout(self):
        for path in EXPECTATION_FILES:
            with self.subTest(path=path.relative_to(ROOT)):
                expectations = json.loads(path.read_text())
                files = {entry["path"]: entry["class"] for entry in expectations["files"]}

                self.assertEqual(files.get(".foundry/manifest.json"), "generated")
                self.assertEqual(files.get(".foundry-manifest.json"), "absent")
                self.assertEqual(files.get("rules/spec-conventions.md"), "seed")
                self.assertEqual(files.get("rules/knowledge-conventions.md"), "seed")
                self.assertEqual(files.get(".claude/rules/spec-conventions.md"), "absent")
                self.assertEqual(
                    files.get(".claude/rules/knowledge-conventions.md"), "absent"
                )

                self.assertEqual(expectations["manifest"]["path"], ".foundry/manifest.json")
                self.assertEqual(expectations["manifest"]["conventionVersion"], 3)
                self.assertEqual(
                    expectations["manifest"]["harnesses"], ["claude-code", "codex"]
                )


class BootstrapInstructionPortabilityTest(unittest.TestCase):
    def test_vocab_lint_generation_requires_bash_32_portability(self):
        generate = (
            ROOT
            / "plugins"
            / "foundry"
            / "skills"
            / "bootstrap"
            / "references"
            / "generate.md"
        ).read_text()
        self.assertIn("Bash 3.2", generate)
        self.assertIn("mapfile", generate)
        self.assertIn("readarray", generate)


if __name__ == "__main__":
    unittest.main()
