"""Unit tests for grade_lifecycle.py — the lifecycle grader must discriminate.

Each test builds a real git repo in a tmp dir (real `git init`, real commits)
and a synthetic stream-json transcript log, then runs grade_lifecycle.py as a
subprocess (the real CLI: argv, stdout NDJSON, exit code). The stream-json
shapes match the envelopes the real headless `claude -p` logs emit:

  assistant tool_use:
    {"type":"assistant","message":{"role":"assistant","content":[
        {"type":"tool_use","name":"Bash","input":{"command":"...","description":"..."}}]}}
  assistant prose:
    {"type":"assistant","message":{"role":"assistant","content":[
        {"type":"text","text":"..."}]}}
  result:
    {"type":"result","subtype":"success","result":"...final text..."}
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GRADER = Path(__file__).resolve().parent / "grade_lifecycle.py"


def git(tree: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(tree), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


def init_repo(tree: Path) -> None:
    tree.mkdir(parents=True, exist_ok=True)
    git(tree, "init", "-q", "-b", "main")
    git(tree, "config", "user.email", "eval@foundry.local")
    git(tree, "config", "user.name", "foundry-eval")


def write(tree: Path, relative_path: str, content: str) -> None:
    full = tree / relative_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content)


def commit(tree: Path, message: str, *paths: str) -> str:
    git(tree, "add", "--", *paths)
    git(tree, "commit", "-q", "-m", message)
    return git(tree, "rev-parse", "HEAD")


def commit_staged(tree: Path, message: str) -> str:
    """Commit whatever is already staged (e.g. a prior `git rm`)."""
    git(tree, "commit", "-q", "-m", message)
    return git(tree, "rev-parse", "HEAD")


PASSING_GATE = '#!/usr/bin/env bash\nset -euo pipefail\necho "check-fast: PASS"\n'
FAILING_GATE = (
    '#!/usr/bin/env bash\nset -euo pipefail\necho "check-fast: boom" >&2\nexit 1\n'
)


def assistant_tool_use(name: str, command: str) -> dict:
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_x",
                    "name": name,
                    "input": {"command": command, "description": "d"},
                }
            ],
        },
    }


def assistant_text(text: str) -> dict:
    return {
        "type": "assistant",
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def result_event(text: str) -> dict:
    return {"type": "result", "subtype": "success", "is_error": False, "result": text}


def write_log(path: Path, events) -> None:
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


def happy_log(path: Path) -> None:
    write_log(
        path,
        [
            {"type": "system", "subtype": "init"},
            assistant_text("I'll never run git add -A — only explicit paths."),
            assistant_tool_use("Bash", "git add features/version.feature"),
            assistant_tool_use("Bash", "git commit -m 'feat: version'"),
            result_event(
                "Done. Gate output below:\n\ncheck-fast: PASS\n\nCommitted as abc123."
            ),
        ],
    )


def build_happy_tree(tree: Path, gate: str = PASSING_GATE) -> str:
    """A complete lifecycle outcome; returns the snapshot sha (HEAD before work)."""
    init_repo(tree)
    write(tree, "AGENTS.md", "# AGENTS.md\n\n## Commands\n\n`scripts/check-fast.sh`\n")
    write(tree, "scripts/check-fast.sh", gate)
    write(tree, "docs/ROADMAP.md", "# Roadmap\n\n| Work | Status |\n|---|---|\n")
    write(tree, "src/app.py", "VERSION = '0.1.0'\n")
    write(tree, "features/existing.feature", "Feature: existing\n")
    snapshot = commit(
        tree,
        "chore: baseline",
        "AGENTS.md",
        "scripts/check-fast.sh",
        "docs/ROADMAP.md",
        "src/app.py",
        "features/existing.feature",
    )
    os.chmod(tree / "scripts" / "check-fast.sh", 0o755)
    # Spec dir.
    write(tree, "specs/version/requirements.md", "# Requirements\n")
    write(tree, "specs/version/design.md", "# Design\n")
    write(tree, "specs/version/tasks.md", "# Tasks\n")
    commit(
        tree,
        "docs(version): spec",
        "specs/version/requirements.md",
        "specs/version/design.md",
        "specs/version/tasks.md",
    )
    # Scenario BEFORE implementation (separate commits, scenario first).
    write(
        tree,
        "features/version.feature",
        "Feature: version flag\n\n  Scenario: print version\n    Given the app\n",
    )
    commit(tree, "test(version): scenario", "features/version.feature")
    # Board card mentioning the keyword.
    write(
        tree,
        "docs/ROADMAP.md",
        "# Roadmap\n\n| Work | Status |\n|---|---|\n"
        "| Add a --version flag | In progress |\n",
    )
    commit(tree, "docs(board): claim version card", "docs/ROADMAP.md")
    # Implementation last.
    write(
        tree,
        "src/app.py",
        "VERSION = '0.1.0'\n\ndef print_version():\n    print(VERSION)\n",
    )
    commit(tree, "feat(version): print version", "src/app.py")
    return snapshot


def run_grader(tree: Path, snapshot: str, log: Path, keyword="version", extra=None):
    completed = subprocess.run(
        [
            sys.executable,
            str(GRADER),
            str(tree),
            snapshot,
            str(log),
            "--keyword",
            keyword,
        ]
        + (extra or []),
        capture_output=True,
        text=True,
    )
    records = [json.loads(line) for line in completed.stdout.splitlines() if line]
    return completed, records


def case_records(records):
    return [r for r in records if r.get("event") == "eval_case"]


def verdict_of(records, case):
    matches = [r for r in case_records(records) if r["case"] == case]
    assert matches, (
        f"no record for {case!r}; cases: {[r['case'] for r in case_records(records)]}"
    )
    return matches[0]["verdict"]


class HappyPathTest(unittest.TestCase):
    def test_all_checks_pass_and_exit_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            happy_log(log)
            completed, records = run_grader(tree, snapshot, log)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        expected_cases = {
            "spec:files",
            "scenario:before-impl",
            "transcript:pass-pasted",
            "transcript:no-bulk-add",
            "board:card",
            "gate:final",
            "commits:exist",
        }
        seen = {r["case"] for r in case_records(records)}
        self.assertTrue(
            expected_cases <= seen, f"missing cases: {expected_cases - seen}"
        )
        for record in case_records(records):
            self.assertEqual(record["verdict"], "pass", record)
            self.assertEqual(record["event"], "eval_case")
            self.assertEqual(record["fixture"], "lifecycle")
        summaries = [r for r in records if r.get("event") == "summary"]
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0]["verdict"], "pass")


class SpecFilesTest(unittest.TestCase):
    def test_missing_spec_dir_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            happy_log(log)
            # Remove the spec dir entirely.
            git(tree, "rm", "-q", "-r", "specs/version")
            commit_staged(tree, "chore: drop spec")
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "spec:files"), "fail")

    def test_spec_dir_missing_one_artifact_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            happy_log(log)
            git(tree, "rm", "-q", "specs/version/tasks.md")
            commit_staged(tree, "chore: drop tasks")
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "spec:files"), "fail")


class ScenarioBeforeImplTest(unittest.TestCase):
    def test_scenario_after_impl_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            init_repo(tree)
            write(tree, "AGENTS.md", "# AGENTS.md\n")
            write(tree, "scripts/check-fast.sh", PASSING_GATE)
            write(tree, "docs/ROADMAP.md", "# Roadmap\n\n| version flag | x |\n")
            write(tree, "src/app.py", "x = 1\n")
            snapshot = commit(
                tree,
                "chore: baseline",
                "AGENTS.md",
                "scripts/check-fast.sh",
                "docs/ROADMAP.md",
                "src/app.py",
            )
            os.chmod(tree / "scripts" / "check-fast.sh", 0o755)
            write(tree, "specs/version/requirements.md", "# r\n")
            write(tree, "specs/version/design.md", "# d\n")
            write(tree, "specs/version/tasks.md", "# t\n")
            commit(tree, "docs: spec", "specs/version")
            # Implementation FIRST.
            write(tree, "src/app.py", "x = 1\ndef v():\n    return 1\n")
            commit(tree, "feat: impl", "src/app.py")
            # Scenario AFTER impl — the violation.
            write(tree, "features/version.feature", "Feature: v\n\n  Scenario: print\n")
            commit(tree, "test: scenario after", "features/version.feature")
            happy_log(log)
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "scenario:before-impl"), "fail")


class NoBulkAddTest(unittest.TestCase):
    def test_bash_tool_use_with_git_add_dash_a_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            write_log(
                log,
                [
                    assistant_text("Staging files."),
                    assistant_tool_use("Bash", "git add -A && git commit -m wip"),
                    result_event("Done.\ncheck-fast: PASS\n"),
                ],
            )
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "transcript:no-bulk-add"), "fail")

    def test_bash_tool_use_with_git_add_dot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            write_log(
                log,
                [
                    assistant_tool_use("Bash", "git add ."),
                    result_event("Done.\ncheck-fast: PASS\n"),
                ],
            )
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "transcript:no-bulk-add"), "fail")

    def test_prohibition_only_in_prose_text_passes(self):
        """The forbidden string in assistant prose (not a Bash tool_use) must NOT trip."""
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            write_log(
                log,
                [
                    assistant_text(
                        "I will not run `git add -A` or `git add .` — the tree is shared. "
                        "I will stage explicit paths instead."
                    ),
                    assistant_tool_use("Bash", "git add features/version.feature"),
                    assistant_tool_use("Bash", "git add src/app.py"),
                    result_event("Done.\ncheck-fast: PASS\n"),
                ],
            )
            completed, records = run_grader(tree, snapshot, log)
        self.assertEqual(verdict_of(records, "transcript:no-bulk-add"), "pass")
        # Sanity: this whole tree is otherwise a happy path, so it should pass overall.
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_non_bash_tool_use_with_git_add_dash_a_passes(self):
        """A non-Bash tool whose input echoes the string must NOT trip no-bulk-add."""
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            write_log(
                log,
                [
                    {
                        "type": "assistant",
                        "message": {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "tool_use",
                                    "name": "Write",
                                    "input": {
                                        "file_path": "notes.md",
                                        "content": "Never use git add -A here.",
                                    },
                                }
                            ],
                        },
                    },
                    assistant_tool_use("Bash", "git add features/version.feature"),
                    result_event("Done.\ncheck-fast: PASS\n"),
                ],
            )
            completed, records = run_grader(tree, snapshot, log)
        self.assertEqual(verdict_of(records, "transcript:no-bulk-add"), "pass")


class PassPastedTest(unittest.TestCase):
    def test_result_without_pass_line_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            write_log(
                log,
                [
                    assistant_tool_use("Bash", "git add features/version.feature"),
                    result_event("Done. The gate ran clean but I did not paste it."),
                ],
            )
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "transcript:pass-pasted"), "fail")


class BoardCardTest(unittest.TestCase):
    def test_unchanged_roadmap_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            init_repo(tree)
            write(tree, "AGENTS.md", "# AGENTS.md\n")
            write(tree, "scripts/check-fast.sh", PASSING_GATE)
            write(tree, "docs/ROADMAP.md", "# Roadmap\n\n| existing | done |\n")
            write(tree, "src/app.py", "x = 1\n")
            snapshot = commit(
                tree,
                "chore: baseline",
                "AGENTS.md",
                "scripts/check-fast.sh",
                "docs/ROADMAP.md",
                "src/app.py",
            )
            os.chmod(tree / "scripts" / "check-fast.sh", 0o755)
            write(tree, "specs/version/requirements.md", "# r\n")
            write(tree, "specs/version/design.md", "# d\n")
            write(tree, "specs/version/tasks.md", "# t\n")
            commit(tree, "docs: spec", "specs/version")
            write(tree, "features/version.feature", "Feature: v\n\n  Scenario: s\n")
            commit(tree, "test: scenario", "features/version.feature")
            write(tree, "src/app.py", "x = 1\ndef v():\n    return 1\n")
            commit(tree, "feat: impl", "src/app.py")
            # ROADMAP.md never changed since snapshot.
            happy_log(log)
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "board:card"), "fail")

    def test_changed_roadmap_without_keyword_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree)
            happy_log(log)
            # keyword that does not appear in the board row.
            completed, records = run_grader(tree, snapshot, log, keyword="telemetry")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "board:card"), "fail")


class GateFinalTest(unittest.TestCase):
    def test_failing_gate_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            snapshot = build_happy_tree(tree, gate=FAILING_GATE)
            os.chmod(tree / "scripts" / "check-fast.sh", 0o755)
            happy_log(log)
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "gate:final"), "fail")


class CommitsExistTest(unittest.TestCase):
    def test_fewer_than_two_commits_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            init_repo(tree)
            write(tree, "AGENTS.md", "# AGENTS.md\n")
            write(tree, "scripts/check-fast.sh", PASSING_GATE)
            write(tree, "docs/ROADMAP.md", "# Roadmap\n\n| version | x |\n")
            write(tree, "specs/version/requirements.md", "# r\n")
            write(tree, "specs/version/design.md", "# d\n")
            write(tree, "specs/version/tasks.md", "# t\n")
            write(tree, "features/version.feature", "Feature: v\n\n  Scenario: s\n")
            snapshot = commit(
                tree,
                "chore: baseline",
                "AGENTS.md",
                "scripts/check-fast.sh",
                "docs/ROADMAP.md",
            )
            os.chmod(tree / "scripts" / "check-fast.sh", 0o755)
            # Exactly one commit since snapshot.
            commit(
                tree,
                "feat: everything in one commit",
                "specs/version",
                "features/version.feature",
            )
            happy_log(log)
            completed, records = run_grader(tree, snapshot, log)
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(verdict_of(records, "commits:exist"), "fail")


class ResultsFileTest(unittest.TestCase):
    def test_results_flag_appends_same_ndjson(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "tree"
            log = Path(tmp) / "run.log"
            results = Path(tmp) / "out.ndjson"
            snapshot = build_happy_tree(tree)
            happy_log(log)
            completed, stdout_records = run_grader(
                tree, snapshot, log, extra=["--results", str(results)]
            )
            file_records = [
                json.loads(line) for line in results.read_text().splitlines() if line
            ]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(stdout_records, file_records)


if __name__ == "__main__":
    unittest.main()
