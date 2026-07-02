"""Migration m003 — harness-agnostic (convention 2 → 3).

Ports the `harness-agnostic` playbook. Moves rules off `.claude/` to top-level `rules/`,
relocates the manifest to `.foundry/manifest.json`, records the inferred harness set, and
rewrites `.claude/rules/` path references. Every primitive is deterministic; the harness
set is inferred from what the repo carries (the playbook's rule).

Idempotent: `applies` keys on the pre-harness-agnostic signals a correct migration removes
(a `.claude/rules/` directory or a top-level `.foundry-manifest.json`).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

CONVENTION = 3
ID = "harness-agnostic"

_LEGACY_MANIFEST = ".foundry-manifest.json"
_NEW_MANIFEST = ".foundry/manifest.json"
# Files whose `.claude/rules/` references are a path, not prose about Claude Code.
_PATH_REF_FILES = ("AGENTS.md", "CLAUDE.md", "scripts/check-fast.sh", ".gitignore")


def applies(repo_root: Path | str) -> bool:
    repo_root = Path(repo_root)
    return (repo_root / ".claude" / "rules").is_dir() or (
        repo_root / _LEGACY_MANIFEST
    ).is_file()


def apply(repo_root: Path | str) -> list[str]:
    repo_root = Path(repo_root)
    _move_rules(repo_root)
    _move_manifest(repo_root)
    harnesses = _infer_harnesses(repo_root)
    _stamp_manifest(repo_root, harnesses)
    flags = _rewrite_path_references(repo_root)
    return flags


def _move_rules(repo_root: Path) -> None:
    src = repo_root / ".claude" / "rules"
    if not src.is_dir():
        return
    dst = repo_root / "rules"
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.iterdir()):
        target = dst / item.name
        if not target.exists():
            shutil.move(str(item), str(target))
    shutil.rmtree(src, ignore_errors=True)
    claude = repo_root / ".claude"
    if claude.is_dir() and not any(claude.iterdir()):
        claude.rmdir()


def _move_manifest(repo_root: Path) -> None:
    src = repo_root / _LEGACY_MANIFEST
    dst = repo_root / _NEW_MANIFEST
    if src.is_file() and not dst.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))


def _infer_harnesses(repo_root: Path) -> list[str]:
    harnesses = []
    if (repo_root / "CLAUDE.md").exists():
        harnesses.append("claude-code")
    if (repo_root / ".codex-plugin").is_dir() or (repo_root / ".agents" / "skills").is_dir():
        harnesses.append("codex")
    return harnesses or ["claude-code"]


def _stamp_manifest(repo_root: Path, harnesses: list[str]) -> None:
    path = repo_root / _NEW_MANIFEST
    manifest = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "pluginVersion": "0", "files": {}
    }
    manifest["conventionVersion"] = CONVENTION
    if not manifest.get("harnesses"):
        manifest["harnesses"] = harnesses
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _rewrite_path_references(repo_root: Path) -> list[str]:
    flags: list[str] = []
    for rel in _PATH_REF_FILES:
        path = repo_root / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if ".claude/rules/" in text:
            path.write_text(text.replace(".claude/rules/", "rules/"), encoding="utf-8")
    flags.append("prose path references outside the known set need review")
    return flags
