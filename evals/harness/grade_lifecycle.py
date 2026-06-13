"""Grade one headless run of the foundry code lifecycle skill.

Usage: grade_lifecycle.py <tree> <snapshot-sha> <transcript-log>
                          --keyword <feature-keyword> [--results <path>]

Reads git history since <snapshot-sha> and the stream-json transcript log, then
emits one NDJSON `eval_case` record per check to stdout (and appends the same
records to --results when given), followed by a `summary` record. Exits nonzero
when any check fails. Pure stdlib.

The lifecycle skill (plugins/foundry/skills/code/SKILL.md) runs seven ordered
stages; the checks below assert the mechanical artifacts each stage leaves
behind, never the agent's self-report:

  spec:files            Stage 1 — specs/<feature>/{requirements,design,tasks}.md.
  scenario:before-impl  Stage 3 gate — the Scenario commit is an ancestor-or-equal
                        of the first implementation commit.
  transcript:pass-pasted Stage 4 gate — the result text pastes `check-fast: PASS`.
  transcript:no-bulk-add Stage 3 rule — no `git add -A|--all|.` in any Bash tool_use.
  board:card            Stage 2 — docs/ROADMAP.md changed and HEAD names the feature.
  gate:final            Stage 4/6 — scripts/check-fast.sh exits 0 at HEAD.
  commits:exist         the run produced >= 2 commits since the snapshot.
"""

import argparse
import json
import os
import re
import subprocess
import sys

FIXTURE = "lifecycle"
GATE_PASS_MARKER = "check-fast: PASS"
GATE_COMMAND = "scripts/check-fast.sh"
SPEC_ARTIFACTS = ("requirements.md", "design.md", "tasks.md")
BULK_ADD_PATTERN = re.compile(r"git\s+add\s+(?:-A\b|--all\b|\.(?:\s|$|&|;|\|))")
SCENARIO_LINE_PATTERN = re.compile(r"^\+\s*Scenario\b")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def git(tree, *args):
    """Run git in the tree; return (returncode, stdout)."""
    completed = subprocess.run(
        ["git", "-C", tree, *args],
        capture_output=True,
        text=True,
    )
    return completed.returncode, completed.stdout


def changed_paths_since(tree, snapshot):
    _, output = git(tree, "diff", "--name-only", f"{snapshot}..HEAD")
    return [line for line in output.splitlines() if line]


def is_test_path(path):
    base = os.path.basename(path)
    return (
        base.startswith("test_")
        or re.search(r"_test\.[^.]+$", base) is not None
        or base.endswith("_test")
    )


def is_implementation_source(path):
    """Implementation = tracked change not under specs/, features/, docs/, not a test."""
    if path.startswith(("specs/", "features/", "docs/")):
        return False
    if is_test_path(path):
        return False
    return True


def first_commit_touching(tree, snapshot, predicate):
    """Oldest commit since the snapshot whose changed files satisfy the predicate."""
    _, revs = git(tree, "rev-list", "--reverse", f"{snapshot}..HEAD")
    for sha in revs.splitlines():
        sha = sha.strip()
        if not sha:
            continue
        _, names = git(tree, "show", "--name-only", "--format=", sha)
        if any(predicate(name) for name in names.splitlines() if name):
            return sha
    return None


def commit_adding_scenario(tree, snapshot):
    """Oldest commit since the snapshot that adds a `Scenario` line to features/*.feature."""
    _, revs = git(tree, "rev-list", "--reverse", f"{snapshot}..HEAD")
    for sha in revs.splitlines():
        sha = sha.strip()
        if not sha:
            continue
        _, diff = git(
            tree,
            "show",
            "--diff-filter=AM",
            "--format=",
            "--unified=0",
            sha,
            "--",
            "features/*.feature",
        )
        for line in diff.splitlines():
            if SCENARIO_LINE_PATTERN.match(line):
                return sha
    return None


def parse_bash_commands(log_path):
    """Every assistant tool_use Bash command string in the stream-json log."""
    commands = []
    content = read_text(log_path)
    if content is None:
        return commands
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") != "assistant":
            continue
        for block in record.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Bash":
                command = block.get("input", {}).get("command")
                if isinstance(command, str):
                    commands.append(command)
    return commands


def result_text(log_path):
    """The final stream-json result event's text, or empty string."""
    text = ""
    content = read_text(log_path)
    if content is None:
        return text
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "result":
            text = record.get("result") or ""
    return text


def find_spec_dir(tree):
    """First specs/<feature>/ holding all three artifacts; (name, missing-list)."""
    specs_root = os.path.join(tree, "specs")
    if not os.path.isdir(specs_root):
        return None, list(SPEC_ARTIFACTS)
    best_missing = None
    for entry in sorted(os.listdir(specs_root)):
        feature_dir = os.path.join(specs_root, entry)
        if not os.path.isdir(feature_dir):
            continue
        missing = [
            artifact
            for artifact in SPEC_ARTIFACTS
            if not os.path.isfile(os.path.join(feature_dir, artifact))
        ]
        if not missing:
            return entry, []
        if best_missing is None or len(missing) < len(best_missing[1]):
            best_missing = (entry, missing)
    if best_missing is not None:
        return best_missing
    return None, list(SPEC_ARTIFACTS)


def check_spec_files(tree):
    feature, missing = find_spec_dir(tree)
    if feature is not None and not missing:
        return True, f"specs/{feature}/ has {', '.join(SPEC_ARTIFACTS)}"
    if feature is None:
        return (
            False,
            "no specs/<feature>/ dir with all of requirements.md, design.md, tasks.md",
        )
    return False, f"specs/{feature}/ is missing {', '.join(missing)}"


def check_scenario_before_impl(tree, snapshot):
    scenario_sha = commit_adding_scenario(tree, snapshot)
    impl_sha = first_commit_touching(tree, snapshot, is_implementation_source)
    if scenario_sha is None:
        return (
            False,
            "no commit since the snapshot adds a Scenario to features/*.feature",
        )
    if impl_sha is None:
        return (
            True,
            f"Scenario committed at {scenario_sha[:8]}; no implementation commit found",
        )
    code, _ = git(tree, "merge-base", "--is-ancestor", scenario_sha, impl_sha)
    if code == 0:
        return (
            True,
            f"Scenario {scenario_sha[:8]} is ancestor-or-equal of first impl {impl_sha[:8]}",
        )
    return (
        False,
        f"Scenario {scenario_sha[:8]} comes AFTER first impl {impl_sha[:8]} (gate violated)",
    )


def check_pass_pasted(log_path):
    text = result_text(log_path)
    if GATE_PASS_MARKER in text:
        return True, f"result text pastes {GATE_PASS_MARKER!r}"
    return False, f"result text does not contain {GATE_PASS_MARKER!r}"


def check_no_bulk_add(log_path):
    for command in parse_bash_commands(log_path):
        if BULK_ADD_PATTERN.search(command):
            return False, f"Bash tool_use ran a bulk add: {command!r}"
    return True, "no `git add -A|--all|.` in any Bash tool_use command"


def check_board_card(tree, snapshot, keyword):
    roadmap = "docs/ROADMAP.md"
    changed = roadmap in changed_paths_since(tree, snapshot)
    if not changed:
        return False, f"{roadmap} did not change since the snapshot"
    content = read_text(os.path.join(tree, roadmap)) or ""
    for line in content.splitlines():
        if line.lstrip().startswith("|") and keyword.lower() in line.lower():
            return True, f"{roadmap} row mentions {keyword!r}"
    return False, f"{roadmap} changed but no row mentions {keyword!r}"


def check_gate_final(tree):
    gate = os.path.join(tree, GATE_COMMAND)
    if not os.path.isfile(gate):
        return False, f"{GATE_COMMAND} not found in the tree"
    completed = subprocess.run(
        ["bash", gate],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True, f"{GATE_COMMAND} exited 0"
    tail = (completed.stdout + completed.stderr).strip().splitlines()[-1:] or [""]
    return False, f"{GATE_COMMAND} exited {completed.returncode}: {tail[0]}"


def check_commits_exist(tree, snapshot):
    code, output = git(tree, "rev-list", "--count", f"{snapshot}..HEAD")
    if code != 0:
        return False, f"cannot count commits since {snapshot[:8]}"
    count = int(output.strip() or "0")
    if count >= 2:
        return True, f"{count} commits since the snapshot"
    return False, f"only {count} commit(s) since the snapshot (need >= 2)"


def grade(tree, snapshot, log_path, keyword):
    yield ("spec:files",) + check_spec_files(tree)
    yield ("scenario:before-impl",) + check_scenario_before_impl(tree, snapshot)
    yield ("transcript:pass-pasted",) + check_pass_pasted(log_path)
    yield ("transcript:no-bulk-add",) + check_no_bulk_add(log_path)
    yield ("board:card",) + check_board_card(tree, snapshot, keyword)
    yield ("gate:final",) + check_gate_final(tree)
    yield ("commits:exist",) + check_commits_exist(tree, snapshot)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tree", help="path to the worked tree to grade")
    parser.add_argument("snapshot", help="HEAD sha before the run")
    parser.add_argument("log", help="path to the stream-json transcript log")
    parser.add_argument(
        "--keyword", required=True, help="feature keyword for the board row"
    )
    parser.add_argument("--results", help="also append NDJSON records to this path")
    args = parser.parse_args()

    results_handle = open(args.results, "a", encoding="utf-8") if args.results else None

    def emit(record):
        line = json.dumps(record)
        print(line)
        if results_handle:
            results_handle.write(line + "\n")

    failed = 0
    for case, ok, detail in grade(args.tree, args.snapshot, args.log, args.keyword):
        emit(
            {
                "event": "eval_case",
                "fixture": FIXTURE,
                "case": case,
                "verdict": "pass" if ok else "fail",
                "detail": detail,
            }
        )
        failed += 0 if ok else 1

    emit(
        {
            "event": "summary",
            "fixture": FIXTURE,
            "verdict": "fail" if failed else "pass",
            "failed": failed,
        }
    )
    if results_handle:
        results_handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
