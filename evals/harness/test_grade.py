"""Unit tests for grade.py — the eval grader must itself discriminate.

Each test builds a fake bootstrapped tree in a tmp dir and runs grade.py as a
subprocess (the real CLI: argv, stdout NDJSON, exit code).
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GRADE = Path(__file__).resolve().parent / "grade.py"

BASE_EXPECTATIONS = {
    "fixture": "fake",
    "gate_command": "scripts/check-fast.sh",
    "files": [
        {"path": "AGENTS.md", "class": "generated"},
        {"path": "CLAUDE.md", "class": "symlink", "target": "AGENTS.md"},
        {"path": "scripts/knowledge.py", "class": "verbatim"},
        {"path": "roadmap/ROADMAP.md", "class": "seed"},
        {"path": "knowledge/knowledge-config.json", "class": "seed"},
        {"path": "features", "class": "dir"},
        {"path": "scripts/agent-env.sh", "class": "absent"},
    ],
    "agents_md": {
        "path": "AGENTS.md",
        "required_sections": ["Commands"],
        "forbidden_sections": ["Logging"],
    },
    "content": [
        {
            "name": "gate-portable",
            "path": "scripts/check-fast.sh",
            "pattern": "/Users/|/home/",
            "must_exist": False,
        },
        {
            "name": "roadmap-epic",
            "path": "roadmap/ROADMAP.md",
            "pattern": "^### Epic 0",
            "must_exist": True,
        },
    ],
    "tree_content": [
        {
            "name": "uses-logger",
            "glob": "src/**/*.py",
            "pattern": "logger\\.(info|warning|error|debug)\\(",
            "must_exist": True,
        },
        {
            "name": "no-print",
            "glob": "src/**/*.py",
            "pattern": "^[ \\t]*print\\(",
            "must_exist": False,
        },
    ],
    "manifest": {
        "path": ".foundry/manifest.json",
        "min_files": 2,
        "conventionVersion": 3,
        "harnesses": ["claude-code", "codex"],
    },
}


def build_complete_tree(root: Path) -> None:
    (root / "scripts").mkdir(parents=True)
    (root / "knowledge").mkdir(parents=True)
    (root / "roadmap").mkdir(parents=True)
    (root / "features").mkdir(parents=True)
    (root / "src" / "app").mkdir(parents=True)
    (root / "src" / "app" / "main.py").write_text(
        "import logging\n\nlogger = logging.getLogger(__name__)\n\n\n"
        "def handle():\n    logger.info('request.handled', extra={'status': 200})\n"
    )
    (root / "AGENTS.md").write_text(
        "# AGENTS.md — fake\n\nIntro.\n\n## Commands\n\n`scripts/check-fast.sh`\n"
    )
    os.symlink("AGENTS.md", root / "CLAUDE.md")
    (root / "scripts" / "knowledge.py").write_text(
        "# foundry-template: knowledge v1\nprint('hi')\n"
    )
    (root / "roadmap" / "ROADMAP.md").write_text(
        "<!-- foundry-seed: roadmap v1 -->\n# Roadmap\n\n### Epic 0 — fake epic\n"
    )
    (root / "knowledge" / "knowledge-config.json").write_text(
        json.dumps({"_foundry_seed": "knowledge-config v1", "types": []})
    )
    (root / "scripts" / "check-fast.sh").write_text(
        '#!/usr/bin/env bash\nset -euo pipefail\necho "check-fast: PASS"\n'
    )
    (root / ".foundry").mkdir()
    (root / ".foundry" / "manifest.json").write_text(
        json.dumps(
            {
                "pluginVersion": "0.2.0",
                "conventionVersion": 3,
                "harnesses": ["claude-code", "codex"],
                "files": {
                    "scripts/knowledge.py": {
                        "template": "knowledge",
                        "version": 1,
                        "sha256": "ab",
                    },
                    ".githooks/pre-push": {
                        "template": "pre-push",
                        "version": 1,
                        "sha256": "cd",
                    },
                },
            }
        )
    )


def run_grade(expectations: dict, tree: Path, extra_args=None):
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as expectations_file:
        json.dump(expectations, expectations_file)
        expectations_path = expectations_file.name
    try:
        completed = subprocess.run(
            [sys.executable, str(GRADE), expectations_path, str(tree)]
            + (extra_args or []),
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(expectations_path)
    records = [json.loads(line) for line in completed.stdout.splitlines() if line]
    return completed, records


def verdict_of(records, case):
    matches = [r for r in records if r["case"] == case]
    assert matches, (
        f"no record for case {case!r}; cases: {[r['case'] for r in records]}"
    )
    return matches[0]["verdict"]


class GradeCompleteTreeTest(unittest.TestCase):
    def test_complete_tree_passes_with_well_formed_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            build_complete_tree(tree)
            completed, records = run_grade(BASE_EXPECTATIONS, tree)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(records)
        for record in records:
            self.assertEqual(record["event"], "eval_case")
            self.assertEqual(record["fixture"], "fake")
            self.assertEqual(record["verdict"], "pass")
            self.assertEqual(
                sorted(record), ["case", "detail", "event", "fixture", "verdict"]
            )


class GradeDiscriminationTest(unittest.TestCase):
    """A grader that cannot fail a broken tree grades nothing."""

    def grade_broken(self, break_tree, expectations=BASE_EXPECTATIONS):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            build_complete_tree(tree)
            break_tree(tree)
            completed, records = run_grade(expectations, tree)
        self.assertNotEqual(completed.returncode, 0)
        return records

    def test_missing_required_file_fails(self):
        records = self.grade_broken(lambda tree: (tree / "AGENTS.md").unlink())
        self.assertEqual(verdict_of(records, "file:AGENTS.md"), "fail")

    def test_verbatim_file_without_marker_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "scripts" / "knowledge.py").write_text("print('hi')\n")
        )
        self.assertEqual(verdict_of(records, "file:scripts/knowledge.py"), "fail")

    def test_seed_file_without_marker_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "roadmap" / "ROADMAP.md").write_text(
                "# Roadmap\n\n### Epic 0 — fake epic\n"
            )
        )
        self.assertEqual(verdict_of(records, "file:roadmap/ROADMAP.md"), "fail")

    def test_symlink_replaced_by_regular_file_fails(self):
        def break_tree(tree):
            (tree / "CLAUDE.md").unlink()
            (tree / "CLAUDE.md").write_text("# copy, not symlink\n")

        records = self.grade_broken(break_tree)
        self.assertEqual(verdict_of(records, "file:CLAUDE.md"), "fail")

    def test_symlink_to_wrong_target_fails(self):
        def break_tree(tree):
            (tree / "CLAUDE.md").unlink()
            os.symlink("roadmap/ROADMAP.md", tree / "CLAUDE.md")

        records = self.grade_broken(break_tree)
        self.assertEqual(verdict_of(records, "file:CLAUDE.md"), "fail")

    def test_forbidden_file_present_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "scripts" / "agent-env.sh").write_text("#!/bin/bash\n")
        )
        self.assertEqual(verdict_of(records, "file:scripts/agent-env.sh"), "fail")

    def test_required_section_missing_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "AGENTS.md").write_text(
                "# AGENTS.md — fake\n\nIntro.\n"
            )
        )
        self.assertEqual(
            verdict_of(records, "agents-section-required:Commands"), "fail"
        )

    def test_forbidden_section_present_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "AGENTS.md").write_text(
                "# AGENTS.md — fake\n\n## Commands\n\n## Logging\n\nwide events\n"
            )
        )
        self.assertEqual(
            verdict_of(records, "agents-section-forbidden:Logging"), "fail"
        )

    def test_required_content_pattern_missing_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "roadmap" / "ROADMAP.md").write_text(
                "<!-- foundry-seed: roadmap v1 -->\n# Roadmap\n"
            )
        )
        self.assertEqual(verdict_of(records, "roadmap-epic"), "fail")

    def test_forbidden_content_pattern_present_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "scripts" / "check-fast.sh").write_text(
                "#!/usr/bin/env bash\nPATH=/Users/someone/.venv/bin:$PATH\n"
            )
        )
        self.assertEqual(verdict_of(records, "gate-portable"), "fail")

    def test_required_tree_content_missing_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "src" / "app" / "main.py").write_text("x = 1\n")
        )
        self.assertEqual(verdict_of(records, "uses-logger"), "fail")

    def test_forbidden_tree_content_present_anywhere_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / "src" / "app" / "debug.py").write_text(
                "import logging\n\nlogger = logging.getLogger()\nprint('debug')\n"
            )
        )
        self.assertEqual(verdict_of(records, "no-print"), "fail")

    def test_manifest_with_too_few_entries_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / ".foundry" / "manifest.json").write_text(
                json.dumps(
                    {
                        "pluginVersion": "0.2.0",
                        "conventionVersion": 3,
                        "harnesses": ["claude-code", "codex"],
                        "files": {},
                    }
                )
            )
        )
        self.assertEqual(verdict_of(records, "manifest:.foundry/manifest.json"), "fail")

    def test_manifest_with_invalid_json_fails(self):
        records = self.grade_broken(
            lambda tree: (tree / ".foundry" / "manifest.json").write_text("not json")
        )
        self.assertEqual(verdict_of(records, "manifest:.foundry/manifest.json"), "fail")

    def test_manifest_with_wrong_convention_version_fails(self):
        def break_tree(tree):
            manifest = json.loads((tree / ".foundry" / "manifest.json").read_text())
            manifest["conventionVersion"] = 2
            (tree / ".foundry" / "manifest.json").write_text(json.dumps(manifest))

        records = self.grade_broken(break_tree)
        self.assertEqual(verdict_of(records, "manifest:.foundry/manifest.json"), "fail")

    def test_manifest_with_wrong_harness_set_fails(self):
        def break_tree(tree):
            manifest = json.loads((tree / ".foundry" / "manifest.json").read_text())
            manifest["harnesses"] = ["claude-code"]
            (tree / ".foundry" / "manifest.json").write_text(json.dumps(manifest))

        records = self.grade_broken(break_tree)
        self.assertEqual(verdict_of(records, "manifest:.foundry/manifest.json"), "fail")


class GradeResultsFileTest(unittest.TestCase):
    def test_results_flag_appends_the_same_ndjson(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            tree.mkdir()
            build_complete_tree(tree)
            results_path = Path(tmp) / "results.ndjson"
            completed, stdout_records = run_grade(
                BASE_EXPECTATIONS, tree, ["--results", str(results_path)]
            )
            file_records = [
                json.loads(line)
                for line in results_path.read_text().splitlines()
                if line
            ]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(stdout_records, file_records)


if __name__ == "__main__":
    unittest.main()
