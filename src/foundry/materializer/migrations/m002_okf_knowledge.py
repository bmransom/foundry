"""Migration m002 — OKF knowledge (convention 1 → 2).

Ports the `okf-knowledge` playbook (v1 update skill). Moves a pre-OKF `docs/` layout to
the OKF `knowledge/` + `roadmap/` convention: relocate concepts and the board, move the
top-level `specs/`, rename `kind:` → `type:` frontmatter, translate the docs config, drop
the old `docs.py` tooling, and stamp `conventionVersion` 2.

Mechanical vs flagged (design D6, the playbook's primitives-vs-judgment split):
- Mechanical (ported in full): the path moves, `kind:`→`type:` rename, config key
  renames, script deletions, manifest stamp.
- Flagged (reported, never guessed): a concept carrying no `kind`/`type` gets the
  playbook's safest type (`reference`) and is listed needs-review; the config's
  `index_title` and free-text prose/path vocabulary are reported, not rewritten.

Idempotent: `applies` keys on the pre-OKF structure a correct migration removes (a `docs/`
directory, `scripts/docs.py`, `docs/docs-config.json`, or a manifest `docs`/`test-docs`
entry), so a migrated repo never re-triggers; `apply` guards every move on existence.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

CONVENTION = 2
ID = "okf-knowledge"
_SAFE_TYPE = "reference"
_CONFIG_KEY_RENAMES = {
    "kinds": "types",
    "doc_globs": "concept_globs",
    "exclude_paths": "reserved_files",
}


def _manifest_path(repo_root: Path) -> Path:
    new = repo_root / ".foundry" / "manifest.json"
    return new if new.is_file() else repo_root / ".foundry-manifest.json"


def _load_manifest(repo_root: Path) -> dict | None:
    path = _manifest_path(repo_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def applies(repo_root: Path | str) -> bool:
    repo_root = Path(repo_root)
    if (repo_root / "docs").is_dir():
        return True
    if (repo_root / "scripts" / "docs.py").is_file():
        return True
    if (repo_root / "docs" / "docs-config.json").is_file():
        return True
    manifest = _load_manifest(repo_root)
    if manifest:
        for entry in manifest.get("files", {}).values():
            if entry.get("template") in ("docs", "test-docs"):
                return True
    return False


def apply(repo_root: Path | str) -> list[str]:
    repo_root = Path(repo_root)
    flags: list[str] = []

    _move_specs(repo_root)
    _move_crate_docs(repo_root)
    flags.extend(_translate_config(repo_root))  # before _move_docs empties docs/
    moved_concepts, moved_board = _move_docs(repo_root)
    for rel in moved_concepts:
        flags.extend(_frontmatter_kind_to_type(repo_root / rel))
    for rel in moved_board:
        _drop_kind(repo_root / rel)
    _delete_old_scripts(repo_root)
    _rewrite_check_fast(repo_root)
    _stamp_manifest(repo_root)
    return flags


# --- moves ---------------------------------------------------------------------------


def _move(src: Path, dst: Path) -> None:
    if not src.exists() or dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst))


def _move_specs(repo_root: Path) -> None:
    _move(repo_root / "specs", repo_root / "roadmap" / "specs")


def _move_crate_docs(repo_root: Path) -> None:
    crates = repo_root / "crates"
    if not crates.is_dir():
        return
    for crate in sorted(crates.iterdir()):
        _move(crate / "docs", crate / "knowledge")


def _move_docs(repo_root: Path) -> tuple[list[str], list[str]]:
    """Move `docs/` into `knowledge/` (concepts) and `roadmap/` (the board); return the
    (concept, board) relpaths that landed, for frontmatter fixes."""
    docs = repo_root / "docs"
    concepts: list[str] = []
    board: list[str] = []
    if not docs.is_dir():
        return concepts, board

    for src in sorted(docs.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(docs)
        if src.name in ("ROADMAP.md", "BACKLOG.md") and rel.parent == Path("."):
            dst = repo_root / "roadmap" / src.name
            board.append(str(dst.relative_to(repo_root)))
        elif src.name == "docs-config.json":
            continue  # handled by _translate_config
        else:
            dst = repo_root / "knowledge" / rel
            if src.suffix == ".md":
                concepts.append(str(dst.relative_to(repo_root)))
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    shutil.rmtree(docs, ignore_errors=True)
    return concepts, board


# --- frontmatter ---------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[list[str] | None, str]:
    """Return (frontmatter lines, remainder) or (None, text) when there is no `---` block."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            return lines[1:i], "".join(lines[i + 1:])
    return None, text


def _frontmatter_kind_to_type(path: Path) -> list[str]:
    """Rename `kind:`→`type:`; add the safest `type:` when neither is present (flagged)."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    if fm is None:
        return []
    flags: list[str] = []
    has_type = any(ln.lstrip().startswith(("type:", "kind:")) for ln in fm)
    out = []
    for ln in fm:
        if ln.lstrip().startswith("kind:"):
            ln = ln.replace("kind:", "type:", 1)
        out.append(ln)
    if not has_type:
        out.append(f"type: {_SAFE_TYPE}\n")
        rel = path.name
        flags.append(f"{rel}: no kind/type — defaulted to '{_SAFE_TYPE}', needs review")
    path.write_text("---\n" + "".join(out) + "---\n" + body, encoding="utf-8")
    return flags


def _drop_kind(path: Path) -> None:
    """Drop the `kind:` field from the board files (no longer concepts)."""
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)
    if fm is None:
        return
    kept = [ln for ln in fm if not ln.lstrip().startswith("kind:")]
    if not any(ln.strip() for ln in kept):
        path.write_text(body.lstrip("\n"), encoding="utf-8")
    else:
        path.write_text("---\n" + "".join(kept) + "---\n" + body, encoding="utf-8")


# --- config --------------------------------------------------------------------------


def _translate_config(repo_root: Path) -> list[str]:
    src = repo_root / "docs" / "docs-config.json"
    if not src.is_file():
        return []
    data = json.loads(src.read_text(encoding="utf-8"))
    out: dict = {}
    for key, value in data.items():
        out[_CONFIG_KEY_RENAMES.get(key, key)] = value
    dst = repo_root / "knowledge" / "knowledge-config.json"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    src.unlink()
    return ["knowledge/knowledge-config.json: index_title/prose vocabulary need review"]


# --- scripts + manifest --------------------------------------------------------------


def _delete_old_scripts(repo_root: Path) -> None:
    for rel in ("scripts/docs.py", "scripts/test_docs.py"):
        path = repo_root / rel
        if path.is_file():
            path.unlink()


def _rewrite_check_fast(repo_root: Path) -> None:
    path = repo_root / "scripts" / "check-fast.sh"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if "docs.py" in text:
        path.write_text(text.replace("docs.py", "knowledge.py"), encoding="utf-8")


def _stamp_manifest(repo_root: Path) -> None:
    path = _manifest_path(repo_root)
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "pluginVersion": "0", "files": {}
    }
    manifest["conventionVersion"] = CONVENTION
    files = manifest.get("files", {})
    for rel, entry in list(files.items()):
        if entry.get("template") in ("docs", "test-docs"):
            files.pop(rel, None)
    manifest["files"] = files
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
