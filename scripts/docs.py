#!/usr/bin/env python3
# foundry-template: docs v1
"""docs — list and lint the curated docs by kind + description.

Dev tooling for agents/humans navigating this repo's docs. Not part of any
product CLI. Zero runtime dependencies (stdlib only).

Config: docs/docs-config.json (relative to repo root). Run without it to see
the bootstrap instructions.
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "docs", "docs-config.json")


def load_config():
    """Load docs/docs-config.json. Exits with a clear message if missing."""
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"docs: config not found at {CONFIG_PATH}\n"
            "Create it from the seed: cp plugins/foundry/templates/seeds/docs/docs-config.json docs/docs-config.json\n"
            "Then edit it for this repo."
        )
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def parse_frontmatter(text):
    """Return (meta, ok). Parse a minimal YAML frontmatter block: a leading
    '---' line, 'key: value' lines, a closing '---'. Values are strings;
    a trailing ' #' comment and surrounding quotes are stripped. ok is False
    when there is no opening '---' or no closing '---'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, False
    meta = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta, True
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        # Strip a trailing ' #' comment only from unquoted values, so a quoted
        # value that legitimately contains ' #' (e.g. "tracked by #1") survives.
        if not val.strip().startswith(('"', "'")) and " #" in val:
            val = val.split(" #", 1)[0]
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return {}, False


def strict_yaml_errors(text):
    """Frontmatter our lenient parser accepts but strict YAML (the VitePress
    site build) rejects: an unquoted scalar containing ': ' parses as a nested
    mapping and breaks the build. Return human-readable errors so `check` (the
    cheap gate) catches what the heavyweight site build would."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return []
    errors = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if not value.startswith(('"', "'")) and ": " in value:
            errors.append(
                f"value for '{key.strip()}' contains ': ' but is unquoted "
                "(strict YAML / VitePress rejects it — wrap the value in quotes)"
            )
    return errors


def infer_crate(relpath):
    parts = relpath.split("/")
    if len(parts) >= 2 and parts[0] == "crates":
        return parts[1]
    return None


def discover(root, config):
    """Return curated docs as dicts sorted by path. Each dict has public keys
    (path, title, description, kind, crate, lifecycle) plus internal _ok/_meta."""
    kinds = config["kinds"]
    doc_globs = config["doc_globs"]
    exclude_substrings = config.get("exclude_substrings", [])
    exclude_prefixes = tuple(config.get("exclude_prefixes", []))

    seen = {}
    for pattern in doc_globs:
        for abspath in glob.glob(os.path.join(root, pattern), recursive=True):
            relpath = os.path.relpath(abspath, root).replace(os.sep, "/")
            if any(s in "/" + relpath for s in exclude_substrings):
                continue
            if exclude_prefixes and relpath.startswith(exclude_prefixes):
                continue
            if relpath in seen:
                continue
            with open(abspath, encoding="utf-8") as handle:
                raw = handle.read()
            meta, ok = parse_frontmatter(raw)
            seen[relpath] = {
                "path": relpath,
                "title": meta.get("title", ""),
                "description": meta.get("description", ""),
                "kind": meta.get("kind", ""),
                "crate": meta.get("crate") or infer_crate(relpath),
                "lifecycle": meta.get("lifecycle", "current") if ok else "",
                "_ok": ok,
                "_meta": meta,
                "_strict": strict_yaml_errors(raw),
            }
    return [seen[k] for k in sorted(seen)]


def validate(doc, config):
    """Return a list of human-readable errors for a discovered doc ([] = clean)."""
    kinds = config["kinds"]
    lifecycles = config.get("lifecycles", ["current", "superseded", "historical"])
    required = config.get("required_fields", ["title", "description", "kind"])

    if not doc["_ok"]:
        return ["missing frontmatter block"]
    meta = doc["_meta"]
    errors = []
    for field in required:
        if not meta.get(field):
            errors.append(f"missing required field '{field}'")
    if meta.get("kind") and meta["kind"] not in kinds:
        errors.append(f"invalid kind '{meta['kind']}' (expected one of {kinds})")
    if meta.get("lifecycle") and meta["lifecycle"] not in lifecycles:
        errors.append(
            f"invalid lifecycle '{meta['lifecycle']}' (expected one of {lifecycles})"
        )
    errors.extend(doc.get("_strict", []))
    return errors


def filter_docs(docs_list, kind, crate, lifecycle):
    result = docs_list
    if kind:
        result = [d for d in result if d["kind"] == kind]
    if crate:
        result = [d for d in result if d["crate"] == crate]
    if lifecycle:
        result = [d for d in result if d["lifecycle"] == lifecycle]
    return result


def public_view(doc):
    return {
        k: doc[k]
        for k in ["path", "title", "description", "kind", "crate", "lifecycle"]
    }


def format_list(docs_list, config):
    """Render docs grouped by kind, one line each, as a string."""
    kinds = config["kinds"]
    out = []
    for kind in kinds:
        group = [d for d in docs_list if d["kind"] == kind]
        if not group:
            continue
        out.append(kind.upper() + (" (dated)" if kind == "decision" else ""))
        for doc in group:
            bits = []
            if doc["crate"]:
                bits.append(doc["crate"])
            if kind == "decision" and doc["_meta"].get("updated"):
                bits.append(doc["_meta"]["updated"])
            tag = f" [{' · '.join(bits)}]" if bits else ""
            out.append(f"  {doc['path']}{tag}  {doc['description']}")
    return "\n".join(out)


def curated(root, config):
    exclude_paths = set(config.get("exclude_paths", []))
    return [d for d in discover(root, config) if d["path"] not in exclude_paths]


def _inline_code_spans(text):
    """Single-backtick spans, skipping fenced ``` code blocks (commands, not refs)."""
    spans = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            spans.extend(re.findall(r"`([^`]+)`", line))
    return spans


def check_skill_refs(root, config):
    """Reference-integrity for .claude/skills/code/SKILL.md: every repo path it names must
    resolve. Literal paths must exist; glob tokens must match >=1 file; '<...>'/'{...}' shapes
    are skipped. Returns a list of human-readable errors ([] = clean; [] when the skill is absent)."""
    skill_path = os.path.join(root, ".claude", "skills", "code", "SKILL.md")
    if not os.path.exists(skill_path):
        return []
    with open(skill_path, encoding="utf-8") as handle:
        raw = handle.read()
    meta, ok = parse_frontmatter(raw)
    if not ok:
        return [".claude/skills/code/SKILL.md: missing frontmatter block"]
    errors = []
    if meta.get("name") != "code":
        errors.append(".claude/skills/code/SKILL.md: frontmatter 'name' must be 'code'")
    if not meta.get("description"):
        errors.append(".claude/skills/code/SKILL.md: missing 'description'")
    skill_ref_prefixes = tuple(config.get("skill_ref_prefixes", []))
    if not skill_ref_prefixes:
        return errors
    # Split each span on whitespace so an embedded path in a compound command span
    # (e.g. `python3 scripts/docs.py check`) is still checked, not just bare-path spans.
    for token in (part for span in _inline_code_spans(raw) for part in span.split()):
        if not token.startswith(skill_ref_prefixes):
            continue
        if any(ch in token for ch in "<>{}"):
            continue  # a reference shape, not a literal path
        if "*" in token:
            if not glob.glob(os.path.join(root, token), recursive=True):
                errors.append(
                    f".claude/skills/code/SKILL.md: glob '{token}' matches no file"
                )
        elif not os.path.exists(os.path.join(root, token.rstrip("/"))):
            errors.append(
                f".claude/skills/code/SKILL.md: reference '{token}' does not exist"
            )
    return errors


def run_check(root, config):
    """Return (exit_code, report_text). Non-zero when any curated doc is invalid."""
    docs_list = curated(root, config)
    lines = []
    for doc in docs_list:
        for error in validate(doc, config):
            lines.append(f"{doc['path']}: {error}")
    lines.extend(check_skill_refs(root, config))
    if lines:
        return 1, "\n".join(lines) + "\ndocs check: FAILED"
    return 0, f"docs check: OK ({len(docs_list)} docs)"


def site_url(path):
    """Map a repo doc path to its VitePress URL (crate docs are synced under docs/)."""
    trimmed = path[:-3] if path.endswith(".md") else path
    if trimmed.startswith("docs/"):
        return "/" + trimmed[len("docs/") :]
    if trimmed.startswith("crates/") and "/docs/" in trimmed:
        crate = trimmed.split("/")[1]
        rest = trimmed.split("/docs/", 1)[1]
        return f"/crates/{crate}/{rest}"
    return "/" + trimmed


def build_sidebar(docs_list, config):
    """VitePress sidebar: one collapsible section per kind, items by title."""
    kinds = config["kinds"]
    sidebar = []
    for kind in kinds:
        items = [
            {"text": d["title"] or d["path"], "link": site_url(d["path"])}
            for d in docs_list
            if d["kind"] == kind
        ]
        if items:
            sidebar.append(
                {
                    "text": kind.capitalize(),
                    "collapsed": kind == "decision",
                    "items": items,
                }
            )
    return sidebar


def sync_site(root, config):
    """Copy crate docs into docs/crates/<crate>/... so VitePress can render them.
    Returns the count staged. The staged tree is gitignored and rebuilt."""
    count = 0
    for doc in curated(root, config):
        path = doc["path"]
        if path.startswith("crates/") and "/docs/" in path:
            crate = path.split("/")[1]
            rest = path.split("/docs/", 1)[1]
            dest = os.path.join(root, "docs", "crates", crate, rest)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(os.path.join(root, path), dest)
            count += 1
    return count


def parse_headings(text):
    """Return list of (level, text, lineno) for every ATX heading in text.
    lineno is 1-based. Only ATX headings (# ... lines) are matched; setext
    headings are ignored."""
    headings = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            headings.append((level, heading_text, lineno))
    return headings


def cmd_outline(doc_path, root):
    """Print the heading tree (level, text, line number) for a doc."""
    abspath = os.path.join(root, doc_path) if not os.path.isabs(doc_path) else doc_path
    if not os.path.exists(abspath):
        print(f"docs outline: file not found: {doc_path}", file=sys.stderr)
        return 1
    with open(abspath, encoding="utf-8") as handle:
        text = handle.read()
    headings = parse_headings(text)
    if not headings:
        print(f"docs outline: no headings found in {doc_path}")
        return 0
    for level, heading_text, lineno in headings:
        indent = "  " * (level - 1)
        print(f"{lineno:4d}  {indent}{'#' * level} {heading_text}")
    return 0


def cmd_section(doc_path, heading_query, root):
    """Print the section matching heading_query (case-insensitive substring)."""
    abspath = os.path.join(root, doc_path) if not os.path.isabs(doc_path) else doc_path
    if not os.path.exists(abspath):
        print(f"docs section: file not found: {doc_path}", file=sys.stderr)
        return 1
    with open(abspath, encoding="utf-8") as handle:
        text = handle.read()
    lines = text.splitlines(keepends=True)
    headings = parse_headings(text)
    if not headings:
        print(f"docs section: no headings found in {doc_path}", file=sys.stderr)
        return 1

    query_lower = heading_query.lower()
    match_index = next(
        (
            i
            for i, (_, heading_text, _) in enumerate(headings)
            if query_lower in heading_text.lower()
        ),
        None,
    )
    if match_index is None:
        available = "\n".join(f"  {heading_text}" for _, heading_text, _ in headings)
        print(
            f"docs section: no heading contains '{heading_query}'. Available headings:\n{available}",
            file=sys.stderr,
        )
        return 1

    start_level, _, start_lineno = headings[match_index]
    # Find end: next heading of equal-or-higher level (lower number = higher level)
    end_lineno = len(lines) + 1
    for level, _, lineno in headings[match_index + 1 :]:
        if level <= start_level:
            end_lineno = lineno
            break

    section_lines = lines[start_lineno - 1 : end_lineno - 1]
    # Strip trailing blank lines for clean output
    while section_lines and section_lines[-1].strip() == "":
        section_lines.pop()
    print("".join(section_lines), end="")
    return 0


def main(argv=None):
    config = load_config()
    kinds = config["kinds"]
    lifecycles = config.get("lifecycles", ["current", "superseded", "historical"])

    parser = argparse.ArgumentParser(prog="docs", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list curated docs grouped by kind")
    p_list.add_argument("--kind", choices=kinds)
    p_list.add_argument("--crate")
    p_list.add_argument("--lifecycle", choices=lifecycles)
    p_list.add_argument("--json", action="store_true", help="machine-readable array")
    p_list.add_argument("--paths", action="store_true", help="bare paths only")

    sub.add_parser("check", help="lint frontmatter; non-zero exit on any error")

    p_sidebar = sub.add_parser("sidebar", help="emit the VitePress sidebar JSON")
    p_sidebar.add_argument("-o", "--output", help="write here instead of stdout")
    sub.add_parser("sync", help="stage crate docs into the site tree")

    p_outline = sub.add_parser("outline", help="print the heading tree of a doc file")
    p_outline.add_argument(
        "doc_path", help="path to the markdown file (repo-relative or absolute)"
    )

    p_section = sub.add_parser("section", help="print one section of a doc file")
    p_section.add_argument(
        "doc_path", help="path to the markdown file (repo-relative or absolute)"
    )
    p_section.add_argument(
        "heading", help="substring to match against heading text (case-insensitive)"
    )

    args = parser.parse_args(argv)

    if args.command == "check":
        code, report = run_check(REPO_ROOT, config)
        stream = sys.stderr if code else sys.stdout
        print(report, file=stream)
        return code

    if args.command == "sidebar":
        payload = json.dumps(
            build_sidebar(curated(REPO_ROOT, config), config), indent=2
        )
        if args.output:
            with open(args.output, "w", encoding="utf-8") as handle:
                handle.write(payload + "\n")
        else:
            print(payload)
        return 0

    if args.command == "sync":
        print(f"docs sync: staged {sync_site(REPO_ROOT, config)} crate docs")
        return 0

    if args.command == "outline":
        return cmd_outline(args.doc_path, REPO_ROOT)

    if args.command == "section":
        return cmd_section(args.doc_path, args.heading, REPO_ROOT)

    docs_list = filter_docs(
        curated(REPO_ROOT, config), args.kind, args.crate, args.lifecycle
    )
    if args.json:
        print(json.dumps([public_view(d) for d in docs_list], indent=2))
    elif args.paths:
        print("\n".join(d["path"] for d in docs_list))
    else:
        print(format_list(docs_list, config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
