"""Knowledge check: port of `knowledge.py check`'s CHECK behavior (design D5) —
frontmatter validity, type/lifecycle enums, skill-reference integrity, and
`knowledge/index.md` freshness. Parameterized by `knowledge/knowledge-config.json`,
same as v1.

`check()` returns `(ok, findings)`; no sys.exit, no argv parsing. Non-check
subcommands (`list`, `outline`, `section`, `sidebar`, `sync`, `index`) stay v1-only —
`scripts/knowledge.py` keeps serving those; only the check path is ported here. When
`knowledge/knowledge-config.json` is absent, the check skips (ok, with a note) — a repo
without a knowledge base isn't a gate failure.
"""

from __future__ import annotations

import glob
import json
import os
import re
from pathlib import Path


def _parse_frontmatter(text: str) -> tuple[dict, bool]:
    """Return (meta, ok). Parse a minimal YAML frontmatter block: a leading
    '---' line, 'key: value' lines, a closing '---'. Values are strings;
    a trailing ' #' comment and surrounding quotes are stripped. ok is False
    when there is no opening '---' or no closing '---'."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, False
    meta: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return meta, True
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        if not val.strip().startswith(('"', "'")) and " #" in val:
            val = val.split(" #", 1)[0]
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return {}, False


def _strict_yaml_errors(text: str) -> list[str]:
    """Frontmatter our lenient parser accepts but strict YAML (the VitePress site
    build) rejects: an unquoted scalar containing ': ' parses as a nested mapping and
    breaks the build."""
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


def _infer_crate(relpath: str) -> str | None:
    parts = relpath.split("/")
    if len(parts) >= 2 and parts[0] == "crates":
        return parts[1]
    return None


def _discover(root: str, config: dict) -> list[dict]:
    """Return curated concepts as dicts sorted by path. Each dict has public keys
    (path, title, description, type, crate, lifecycle) plus internal _ok/_meta."""
    concept_globs = config["concept_globs"]
    exclude_substrings = config.get("exclude_substrings", [])
    exclude_prefixes = tuple(config.get("exclude_prefixes", []))

    seen: dict[str, dict] = {}
    for pattern in concept_globs:
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
            meta, ok = _parse_frontmatter(raw)
            seen[relpath] = {
                "path": relpath,
                "title": meta.get("title", ""),
                "description": meta.get("description", ""),
                "type": meta.get("type", ""),
                "crate": meta.get("crate") or _infer_crate(relpath),
                "lifecycle": meta.get("lifecycle", "current") if ok else "",
                "_ok": ok,
                "_meta": meta,
                "_strict": _strict_yaml_errors(raw),
            }
    return [seen[k] for k in sorted(seen)]


def _validate(concept: dict, config: dict) -> list[str]:
    """Return a list of human-readable errors for a discovered concept ([] = clean)."""
    types = config["types"]
    lifecycles = config.get("lifecycles", ["current", "superseded", "historical"])
    required = config.get("required_fields", ["title", "description", "type"])

    if not concept["_ok"]:
        return ["missing frontmatter block"]
    meta = concept["_meta"]
    errors = []
    for field in required:
        if not meta.get(field):
            errors.append(f"missing required field '{field}'")
    if meta.get("type") and meta["type"] not in types:
        errors.append(f"invalid type '{meta['type']}' (expected one of {types})")
    if meta.get("lifecycle") and meta["lifecycle"] not in lifecycles:
        errors.append(
            f"invalid lifecycle '{meta['lifecycle']}' (expected one of {lifecycles})"
        )
    errors.extend(concept.get("_strict", []))
    return errors


def _curated(root: str, config: dict) -> list[dict]:
    reserved = set(config.get("reserved_files", []))
    return [c for c in _discover(root, config) if c["path"] not in reserved]


def _inline_code_spans(text: str) -> list[str]:
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


def _check_skill_refs(root: str, config: dict) -> list[str]:
    """Reference-integrity for .claude/skills/code/SKILL.md: every repo path it names
    must resolve. Literal paths must exist; glob tokens must match >=1 file;
    '<...>'/'{...}' shapes are skipped. Returns [] when the skill file is absent."""
    skill_path = os.path.join(root, ".claude", "skills", "code", "SKILL.md")
    if not os.path.exists(skill_path):
        return []
    with open(skill_path, encoding="utf-8") as handle:
        raw = handle.read()
    meta, ok = _parse_frontmatter(raw)
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
    for token in (part for span in _inline_code_spans(raw) for part in span.split()):
        if not token.startswith(skill_ref_prefixes):
            continue
        if any(ch in token for ch in "<>{}"):
            continue
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


def _site_url(path: str) -> str:
    """Map a repo concept path to its VitePress URL (crate concepts sync under knowledge/)."""
    trimmed = path[:-3] if path.endswith(".md") else path
    if trimmed.startswith("knowledge/"):
        return "/" + trimmed[len("knowledge/") :]
    if trimmed.startswith("crates/") and "/knowledge/" in trimmed:
        crate = trimmed.split("/")[1]
        rest = trimmed.split("/knowledge/", 1)[1]
        return f"/crates/{crate}/{rest}"
    return "/" + trimmed


def _noncurrent_lifecycle(concept: dict) -> str:
    lifecycle = concept.get("lifecycle") or "current"
    return "" if lifecycle == "current" else lifecycle


def _current_first(group: list[dict]) -> list[dict]:
    return sorted(group, key=lambda c: bool(_noncurrent_lifecycle(c)))


def _build_index(concepts: list[dict], config: dict) -> str:
    """OKF bundle-root index (§6), same shape `knowledge.py index` writes."""
    types = config["types"]
    title = config.get("index_title", "Knowledge")
    okf_version = config.get("okf_version", "0.1")
    out = ["---", f"okf_version: {okf_version}", "---", "", f"# {title}", ""]
    for type_name in types:
        group = [c for c in concepts if c["type"] == type_name]
        if not group:
            continue
        out.append(f"## {type_name.capitalize()}")
        out.append("")
        for concept in _current_first(group):
            label = concept["title"] or concept["path"]
            link = _site_url(concept["path"])
            desc = concept["description"]
            entry = f"* [{label}]({link}) - {desc}" if desc else f"* [{label}]({link})"
            lifecycle = _noncurrent_lifecycle(concept)
            if lifecycle:
                entry += f" _({lifecycle})_"
            out.append(entry)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def _check_index_fresh(root: str, config: dict) -> list[str]:
    """The committed knowledge/index.md must match a fresh index generation."""
    expected = _build_index(_curated(root, config), config)
    index_abs = os.path.join(root, "knowledge", "index.md")
    actual = ""
    if os.path.exists(index_abs):
        with open(index_abs, encoding="utf-8") as handle:
            actual = handle.read()
    if actual != expected:
        return [
            "knowledge/index.md is stale — regenerate with "
            "`python3 scripts/knowledge.py index`"
        ]
    return []


def check(repo_root: Path | str) -> tuple[bool, list[str]]:
    """Validate every curated concept's frontmatter, skill-ref integrity, and index
    freshness. Returns (ok, findings) — findings are prefixed `knowledge:`.
    """
    repo_root = Path(repo_root)
    config_path = repo_root / "knowledge" / "knowledge-config.json"
    if not config_path.is_file():
        return True, ["knowledge: skipped (no knowledge/knowledge-config.json)"]

    config = json.loads(config_path.read_text(encoding="utf-8"))
    root = str(repo_root)

    violations: list[str] = []
    for concept in _curated(root, config):
        for error in _validate(concept, config):
            violations.append(f"{concept['path']}: {error}")
    violations.extend(_check_skill_refs(root, config))
    violations.extend(_check_index_fresh(root, config))

    findings = [f"knowledge: {v}" for v in violations]
    return not violations, findings
