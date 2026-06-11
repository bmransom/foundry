"""Grade a bootstrapped tree against a fixture's expectations.json.

Usage: grade.py <expectations.json> <tree> [--results <path>]

Emits one NDJSON record per assertion case to stdout (and appends the same
records to --results when given):

    {"event": "eval_case", "fixture": ..., "case": ..., "verdict": "pass|fail",
     "detail": ...}

Exits nonzero when any case fails. Pure stdlib.

Expectations schema (all top-level keys optional except "fixture"):
  files:     [{"path", "class": generated|verbatim|seed|symlink|dir|absent,
               "target" (symlink only)}]
  agents_md: {"path", "required_sections": [...], "forbidden_sections": [...]}
  content:   [{"name"?, "path", "pattern", "must_exist"}]
             — patterns compile with re.MULTILINE | re.DOTALL, so "^### Epic 0"
               anchors lines and "a.*b" asserts ordering across lines.
  manifest:  {"path", "min_files"} — JSON with >= min_files entries in "files".
  gate_command, defects: read by bootstrap-eval.sh, ignored here.
"""

import argparse
import json
import os
import re
import sys

VERBATIM_MARKER = "foundry-template:"
SEED_MARKERS = ("foundry-seed", "_foundry_seed")


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return None


def check_file(tree, spec):
    path = spec["path"]
    file_class = spec["class"]
    full = os.path.join(tree, path)

    if file_class == "absent":
        if os.path.lexists(full):
            return False, f"{path} must not exist for this fixture, but does"
        return True, f"{path} absent as expected"

    if file_class == "dir":
        if not os.path.isdir(full):
            return False, f"missing directory {path}"
        return True, f"directory {path} present"

    if file_class == "symlink":
        if not os.path.islink(full):
            return False, f"{path} is not a symlink"
        target = os.readlink(full)
        if target != spec["target"]:
            return False, f"{path} points at {target}, expected {spec['target']}"
        return True, f"{path} -> {spec['target']}"

    if not os.path.isfile(full):
        return False, f"missing file {path}"

    content = read_text(full)
    if file_class == "verbatim" and VERBATIM_MARKER not in content:
        return False, f"{path} lacks the {VERBATIM_MARKER} marker"
    if file_class == "seed" and not any(marker in content for marker in SEED_MARKERS):
        return False, f"{path} lacks a foundry-seed marker"
    return True, f"{path} present ({file_class})"


def section_pattern(name):
    return re.compile(rf"(?m)^##\s+{re.escape(name)}\s*$")


def check_sections(tree, agents_md):
    path = agents_md.get("path", "AGENTS.md")
    content = read_text(os.path.join(tree, path))
    for name in agents_md.get("required_sections", []):
        case = f"agents-section-required:{name}"
        if content is None:
            yield case, False, f"{path} unreadable"
        elif section_pattern(name).search(content):
            yield case, True, f"## {name} present in {path}"
        else:
            yield case, False, f"## {name} missing from {path}"
    for name in agents_md.get("forbidden_sections", []):
        case = f"agents-section-forbidden:{name}"
        if content is None:
            yield case, False, f"{path} unreadable"
        elif section_pattern(name).search(content):
            yield case, False, f"## {name} present in {path} but forbidden"
        else:
            yield case, True, f"## {name} absent from {path} as expected"


def check_content(tree, spec):
    path = spec["path"]
    pattern = spec["pattern"]
    must_exist = spec["must_exist"]
    content = read_text(os.path.join(tree, path))
    if content is None:
        return False, f"{path} unreadable"
    found = re.search(pattern, content, re.MULTILINE | re.DOTALL) is not None
    if found and not must_exist:
        return False, f"forbidden pattern {pattern!r} found in {path}"
    if not found and must_exist:
        return False, f"required pattern {pattern!r} not found in {path}"
    verb = "found" if found else "absent"
    return True, f"pattern {pattern!r} {verb} in {path} as expected"


def check_manifest(tree, spec):
    path = spec["path"]
    min_files = spec["min_files"]
    content = read_text(os.path.join(tree, path))
    if content is None:
        return False, f"missing manifest {path}"
    try:
        manifest = json.loads(content)
    except json.JSONDecodeError as error:
        return False, f"{path} is not valid JSON: {error}"
    entries = manifest.get("files")
    if not isinstance(entries, dict):
        return False, f'{path} lacks a "files" object'
    if len(entries) < min_files:
        return False, f"{path} records {len(entries)} files, expected >= {min_files}"
    return True, f"{path} records {len(entries)} files (>= {min_files})"


def grade(expectations, tree):
    for spec in expectations.get("files", []):
        ok, detail = check_file(tree, spec)
        yield f"file:{spec['path']}", ok, detail
    if "agents_md" in expectations:
        yield from check_sections(tree, expectations["agents_md"])
    for spec in expectations.get("content", []):
        case = spec.get("name", f"content:{spec['path']}:{spec['pattern']}")
        ok, detail = check_content(tree, spec)
        yield case, ok, detail
    if "manifest" in expectations:
        spec = expectations["manifest"]
        ok, detail = check_manifest(tree, spec)
        yield f"manifest:{spec['path']}", ok, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("expectations", help="path to expectations.json")
    parser.add_argument("tree", help="path to the bootstrapped tree to grade")
    parser.add_argument("--results", help="also append NDJSON records to this path")
    args = parser.parse_args()

    with open(args.expectations, encoding="utf-8") as handle:
        expectations = json.load(handle)
    fixture = expectations["fixture"]

    results_handle = open(args.results, "a", encoding="utf-8") if args.results else None
    failed = 0
    for case, ok, detail in grade(expectations, args.tree):
        record = json.dumps(
            {
                "event": "eval_case",
                "fixture": fixture,
                "case": case,
                "verdict": "pass" if ok else "fail",
                "detail": detail,
            }
        )
        print(record)
        if results_handle:
            results_handle.write(record + "\n")
        failed += 0 if ok else 1
    if results_handle:
        results_handle.close()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
