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

  spec:files            Stage 1 — roadmap/specs/<feature>/{requirements,design,tasks}.md.
  scenario:before-impl  Stage 3 work order — in the transcript, the first action that
                        writes a features/*.feature file occurs at or before the first
                        action that writes implementation source. The skill mandates
                        ORDER, not commit granularity, so this reads the transcript
                        rather than commit ancestry (vacuous under one atomic commit).
  transcript:pass-pasted Stage 4 gate — the result text pastes `check-fast: PASS`.
  transcript:no-bulk-add Stage 3 rule — no `git add -A|--all|.` in any Bash tool_use.
  board:card            Stage 2 — roadmap/ROADMAP.md changed and HEAD names the feature.
  gate:final            Stage 4/6 — scripts/check-fast.sh exits 0 at HEAD.
  commits:exist         the run produced >= 1 commit since the snapshot.
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
NON_IMPL_DIRS = ("roadmap", "features", "knowledge")
FILE_WRITING_TOOLS = ("Write", "Edit")


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


def path_segments(path):
    """The path split into directory/file segments, regardless of absolute/relative."""
    return [segment for segment in path.replace("\\", "/").split("/") if segment]


def is_test_path(path):
    base = os.path.basename(path)
    segments = path_segments(path)
    return (
        base.startswith("test_")
        or re.search(r"_test\.[^.]+$", base) is not None
        or base.endswith("_test")
        or "tests" in segments
    )


def is_feature_file(path):
    """A Gherkin feature file: under features/ and named *.feature."""
    segments = path_segments(path)
    return "features" in segments and path.endswith(".feature")


def is_implementation_source(path):
    """Implementation = not under roadmap/, features/, knowledge/, and not a test.

    Uses path-segment containment so it classifies absolute transcript file_paths
    (e.g. /tmp/tree/src/main.rs) the same as repo-relative ones.
    """
    segments = path_segments(path)
    if any(directory in segments for directory in NON_IMPL_DIRS):
        return False
    if is_test_path(path):
        return False
    return True


def iter_tool_uses(log_path):
    """Every assistant tool_use block in transcript order, as (name, input dict)."""
    content = read_text(log_path)
    if content is None:
        return
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
            if block.get("type") == "tool_use":
                yield block.get("name"), block.get("input", {}) or {}


def parse_bash_commands(log_path):
    """Every assistant tool_use Bash command string in the stream-json log."""
    commands = []
    for name, tool_input in iter_tool_uses(log_path):
        if name == "Bash":
            command = tool_input.get("command")
            if isinstance(command, str):
                commands.append(command)
    return commands


def first_feature_and_impl_actions(log_path):
    """Index of the first feature-file write and the first impl-source write.

    Scans assistant tool_uses in transcript order. A Write/Edit is classified by
    its input.file_path. Bash file-creating heredocs/touch are NOT decoded — Write
    and Edit are the normal path the agent takes; treating Bash command text as a
    file write would misclassify e.g. `git add features/x.feature`. Returns
    (feature_index, impl_index); either is None when no such action is seen.
    """
    feature_index = None
    impl_index = None
    position = 0
    for name, tool_input in iter_tool_uses(log_path):
        if name in FILE_WRITING_TOOLS:
            file_path = tool_input.get("file_path")
            if isinstance(file_path, str):
                if feature_index is None and is_feature_file(file_path):
                    feature_index = position
                if impl_index is None and is_implementation_source(file_path):
                    impl_index = position
        position += 1
    return feature_index, impl_index


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
    """First roadmap/specs/<feature>/ holding all three artifacts; (name, missing-list)."""
    specs_root = os.path.join(tree, "roadmap", "specs")
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
        return True, f"roadmap/specs/{feature}/ has {', '.join(SPEC_ARTIFACTS)}"
    if feature is None:
        return (
            False,
            "no roadmap/specs/<feature>/ dir with all of requirements.md, design.md, tasks.md",
        )
    return False, f"roadmap/specs/{feature}/ is missing {', '.join(missing)}"


def check_scenario_before_impl(log_path):
    """Stage 3 work order, read from the transcript, not commit ancestry.

    The first features/*.feature write must occur at or before the first
    implementation-source write. No feature write at all means the discipline was
    skipped (fail). A feature write with no impl write means the scenario was
    written and impl may have arrived via other means (pass — don't penalize).
    """
    feature_index, impl_index = first_feature_and_impl_actions(log_path)
    if feature_index is None:
        return False, "no features/*.feature file written before impl source"
    if impl_index is None:
        return True, "feature file written; no impl source write seen (not penalized)"
    if feature_index <= impl_index:
        return True, "feature file first written before impl source"
    return False, "impl source written before any features/*.feature file"


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
    roadmap = "roadmap/ROADMAP.md"
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
    if count >= 1:
        return True, f"{count} commit(s) since the snapshot"
    return False, "no commits since the snapshot (need >= 1)"


def grade(tree, snapshot, log_path, keyword):
    yield ("spec:files",) + check_spec_files(tree)
    yield ("scenario:before-impl",) + check_scenario_before_impl(log_path)
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
