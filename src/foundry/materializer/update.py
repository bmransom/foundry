"""`foundry update` (design D6, AC-7.3): re-sync a bootstrapped repo with the packaged
templates, crossing any convention break first.

Flow over a repo root:
1. Read the manifest (`.foundry/manifest.json`, legacy `.foundry-manifest.json`). No
   manifest → **legacy backfill**: detect verbatim files by their `foundry-template:`
   markers, record the pristine ones, flag the customized ones, and write a manifest.
2. Run migration modules in ascending order from the repo's convention to the registry
   head; each module's `applies(repo_root)` guards it.
3. Hash-compare every **tracked** verbatim file: pristine-but-outdated (package version
   bumped) refreshes byte-exact and restamps; a hash mismatch is flagged customized and
   never overwritten.
4. A refreshed `scripts/knowledge.py` regenerates `knowledge/index.md` — the index is
   that script's generated output, so a generator refresh otherwise leaves it stale and
   the repo's gate red. No prompt: generated files carry no user content to protect.
5. Restamp `pluginVersion` + `conventionVersion`.

Idempotent: a second run over a current repo reports nothing to do. `--dry-run` prints the
plan without writing. Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from foundry import __version__
from foundry.materializer.bootstrap import verbatim_root

HEAD = 5  # registry head (matches the highest migration module's CONVENTION)

_MARKER_RE = re.compile(r"foundry-template:\s*(\S+)\s+v(\d+)")
_NEW_MANIFEST = ".foundry/manifest.json"
_LEGACY_MANIFEST = ".foundry-manifest.json"


@dataclass
class UpdateResult:
    actions: list[str] = field(default_factory=list)
    refreshed: list[str] = field(default_factory=list)
    customized: list[str] = field(default_factory=list)
    migrated: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    backfilled: bool = False

    @property
    def changes(self) -> int:
        return len(self.actions)


# --- migration registry --------------------------------------------------------------


def _migrations() -> list:
    """The migration modules, ascending by convention. Lazily imported so the module has
    no import cycle with the migration package (which imports helpers from here)."""
    from foundry.materializer.migrations import (
        m002_okf_knowledge,
        m003_harness_agnostic,
        m004_card_ids,
        m005_pinned_run,
    )

    return [m002_okf_knowledge, m003_harness_agnostic, m004_card_ids, m005_pinned_run]


# --- manifest helpers ----------------------------------------------------------------


def _manifest_path(repo_root: Path) -> Path:
    new = repo_root / _NEW_MANIFEST
    if new.is_file():
        return new
    legacy = repo_root / _LEGACY_MANIFEST
    if legacy.is_file():
        return legacy
    return new


def _load_manifest(repo_root: Path) -> dict | None:
    path = _manifest_path(repo_root)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(repo_root: Path, manifest: dict) -> None:
    path = _manifest_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _marker(text: str) -> tuple[str, int] | None:
    m = _MARKER_RE.search(text)
    return (m.group(1), int(m.group(2))) if m else None


def _strip_markers(text: str) -> str:
    return "".join(ln for ln in text.splitlines(keepends=True) if "foundry-template:" not in ln)


# --- legacy backfill -----------------------------------------------------------------


def _backfill_manifest(repo_root: Path, result: UpdateResult, *, dry_run: bool) -> dict:
    """Detect installed verbatim files by their markers and write a fresh manifest.

    A file whose content (modulo its marker) equals the current template is recorded
    pristine at its marker version; a file that diverges is recorded against the current
    template hash so the verbatim compare below flags it customized — never overwritten.
    """
    root = verbatim_root()
    files: dict[str, dict] = {}
    for source in sorted(root.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        rel = str(source.relative_to(root))
        installed = repo_root / rel
        if not installed.is_file():
            continue
        disk = installed.read_bytes()
        marker = _marker(disk.decode("utf-8", "replace"))
        if not marker:
            continue
        name, version = marker
        package = source.read_bytes()
        if _strip_markers(disk.decode("utf-8", "replace")) == _strip_markers(
            package.decode("utf-8", "replace")
        ):
            files[rel] = {
                "template": name, "version": version,
                "sha256": hashlib.sha256(disk).hexdigest(),
            }
        else:
            files[rel] = {
                "template": name, "version": version,
                "sha256": hashlib.sha256(package).hexdigest(),
            }
            result.needs_review.append(f"{rel}: customized (backfill undecidable)")
    manifest = {
        "pluginVersion": __version__,
        "conventionVersion": _infer_convention(repo_root),
        "harnesses": ["claude-code"],
        "files": files,
    }
    result.backfilled = True
    result.actions.append(f"{_p(dry_run)}backfill manifest ({len(files)} tracked file(s))")
    if not dry_run:
        _write_manifest(repo_root, manifest)
    return manifest


def _infer_convention(repo_root: Path) -> int:
    """Place a manifest-less repo by structure (earliest signal wins)."""
    if (repo_root / "docs").is_dir() or (repo_root / "scripts" / "docs.py").is_file():
        return 1
    if (repo_root / ".claude" / "rules").is_dir() or (repo_root / _LEGACY_MANIFEST).is_file():
        return 2
    board = repo_root / "roadmap" / "ROADMAP.md"
    if board.is_file() and "| Id " not in board.read_text(encoding="utf-8"):
        from foundry.materializer.migrations import m004_card_ids

        if any(m004_card_ids._is_card_header(ln)
               for ln in board.read_text(encoding="utf-8").splitlines()):
            return 3
    for rel in ("scripts/check-board.py", "scripts/prose-lint.py"):
        if (repo_root / rel).is_file():
            return 4
    return HEAD


# --- verbatim compare ----------------------------------------------------------------


def _compare_verbatim(repo_root: Path, manifest: dict, result: UpdateResult, *, dry_run: bool) -> None:
    root = verbatim_root()
    files = manifest.get("files", {})
    for rel, entry in files.items():
        installed = repo_root / rel
        source = root / rel
        if not source.is_file() or not installed.is_file():
            continue
        package = source.read_bytes()
        pkg_marker = _marker(package.decode("utf-8", "replace"))
        pkg_version = pkg_marker[1] if pkg_marker else entry.get("version", 0)
        disk_hash = hashlib.sha256(installed.read_bytes()).hexdigest()
        if disk_hash != entry.get("sha256"):
            result.customized.append(rel)
            result.actions.append(f"customized {rel} — left untouched")
            continue
        if pkg_version > entry.get("version", 0):
            result.refreshed.append(rel)
            result.actions.append(f"{_p(dry_run)}refresh {rel} (v{entry.get('version')}→v{pkg_version})")
            if not dry_run:
                installed.write_bytes(package)
                if source.stat().st_mode & stat.S_IXUSR:
                    installed.chmod(0o755)
                entry["version"] = pkg_version
                entry["sha256"] = hashlib.sha256(package).hexdigest()
    if result.refreshed and not dry_run:
        _write_manifest(repo_root, manifest)


# --- driver --------------------------------------------------------------------------


def _p(dry_run: bool) -> str:
    return "would " if dry_run else ""


def update(repo_root: Path | str, *, dry_run: bool = False) -> UpdateResult:
    repo_root = Path(repo_root)
    result = UpdateResult()

    manifest = _load_manifest(repo_root)
    if manifest is None:
        manifest = _backfill_manifest(repo_root, result, dry_run=dry_run)

    convention = manifest.get("conventionVersion")
    if convention is None:
        convention = _infer_convention(repo_root)
    _run_migrations(repo_root, result, convention, dry_run=dry_run)

    # Re-read: a migration may have moved or restamped the manifest.
    manifest = _load_manifest(repo_root) or manifest
    _compare_verbatim(repo_root, manifest, result, dry_run=dry_run)
    _regenerate_index(repo_root, result, dry_run=dry_run)
    _sync_pin(repo_root, manifest, result, dry_run=dry_run)

    _restamp(repo_root, manifest, result, dry_run=dry_run)
    return result


# The pinned gate command a conv-5 hook or CI step carries (m005's shape).
_UVX_GATE_RE = re.compile(r'uvx --from "git\+[^"]+@([^"]+)" foundry gate')
_PRE_PUSH_REL = ".githooks/pre-push"


def _sync_pin(repo_root: Path, manifest: dict, result: UpdateResult, *, dry_run: bool) -> None:
    """The config pin (`[foundry] pin`) is the single source: a pristine pre-push
    hook (and any CI gate line) carrying a different tag is rewritten to it, hash
    re-recorded so pristine stays pristine. A customized hook is never touched —
    flagged when its pin drifts."""
    pin, repo_url = _config_pin(repo_root)
    if not pin or not repo_url:
        return
    desired = f'uvx --from "git+{repo_url}@{pin}" foundry gate'

    hook = repo_root / _PRE_PUSH_REL
    entry = manifest.get("files", {}).get(_PRE_PUSH_REL)
    if hook.is_file() and entry is not None:
        raw = hook.read_bytes()
        text = raw.decode("utf-8", "replace")
        match = _UVX_GATE_RE.search(text)
        if match and match.group(0) != desired:
            if hashlib.sha256(raw).hexdigest() != entry.get("sha256"):
                result.actions.append("customized .githooks/pre-push — pin left as-is")
            else:
                result.actions.append(
                    f"{_p(dry_run)}repin {_PRE_PUSH_REL} (@{match.group(1)} → @{pin})"
                )
                if not dry_run:
                    new = text.replace(match.group(0), desired)
                    hook.write_bytes(new.encode("utf-8"))
                    entry["sha256"] = hashlib.sha256(new.encode("utf-8")).hexdigest()
                    _write_manifest(repo_root, manifest)

    wf_dir = repo_root / ".github" / "workflows"
    if wf_dir.is_dir():
        for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
            text = wf.read_text(encoding="utf-8")
            new, n = _UVX_GATE_RE.subn(
                lambda m: desired if m.group(0) != desired else m.group(0), text
            )
            if new != text:
                rel = wf.relative_to(repo_root)
                result.actions.append(f"{_p(dry_run)}repin {rel} (→ @{pin})")
                if not dry_run:
                    wf.write_text(new, encoding="utf-8")


_KNOWLEDGE_SCRIPT = "scripts/knowledge.py"


def _regenerate_index(repo_root: Path, result: UpdateResult, *, dry_run: bool) -> None:
    """Regenerate `knowledge/index.md` when the knowledge script was refreshed.

    The index is the script's generated output; hand-edits are already forbidden by
    its staleness check, so regeneration is the mechanical consequence of the refresh
    — never a prompt. The script is stdlib-only by contract, so foundry's own
    interpreter runs it."""
    if _KNOWLEDGE_SCRIPT not in result.refreshed:
        return
    script = repo_root / _KNOWLEDGE_SCRIPT
    if not script.is_file() or not (repo_root / "knowledge").is_dir():
        return
    result.actions.append(f"{_p(dry_run)}regenerate knowledge/index.md")
    if dry_run:
        return
    proc = subprocess.run(
        [sys.executable, str(script), "index"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        result.actions.append(
            f"knowledge index regeneration failed (exit {proc.returncode}) — "
            f"run: python3 {_KNOWLEDGE_SCRIPT} index"
        )


def _run_migrations(repo_root: Path, result: UpdateResult, convention: int, *, dry_run: bool) -> None:
    """Run every migration above the repo's convention, ascending. The convention range is
    the plan (design D6 — "from the repo's convention to the head"); `applies()` guards the
    real apply so a partially-migrated or precondition-absent step is skipped."""
    pin, repo_url = _config_pin(repo_root)
    for mod in _migrations():
        if mod.CONVENTION <= convention:
            continue
        if not dry_run and not mod.applies(repo_root):
            continue
        result.migrated.append(mod.ID)
        result.actions.append(f"{_p(dry_run)}migrate {mod.ID} (→ convention {mod.CONVENTION})")
        if dry_run:
            continue
        kwargs = {}
        if mod.ID == "pinned-run":
            if pin:
                kwargs["pin"] = pin
            if repo_url:
                kwargs["repo_url"] = repo_url
        flags = mod.apply(repo_root, **kwargs)
        if flags:
            result.needs_review.extend(flags)


def _config_pin(repo_root: Path) -> tuple[str | None, str | None]:
    try:
        from foundry.config import Config

        config = Config.load(repo_root)
        return config.pin, config.repo_url
    except Exception:
        return None, None


def _restamp(repo_root: Path, manifest: dict, result: UpdateResult, *, dry_run: bool) -> None:
    manifest = _load_manifest(repo_root) or manifest
    stale_plugin = manifest.get("pluginVersion") != __version__
    stale_conv = manifest.get("conventionVersion") != HEAD
    if not (stale_plugin or stale_conv):
        return
    result.actions.append(f"{_p(dry_run)}restamp manifest (plugin {__version__}, convention {HEAD})")
    if dry_run:
        return
    manifest["pluginVersion"] = __version__
    manifest["conventionVersion"] = HEAD
    _write_manifest(repo_root, manifest)


# --- CLI surface ---------------------------------------------------------------------


def run(repo_root: Path | str, *, dry_run: bool = False) -> list[str]:
    result = update(repo_root, dry_run=dry_run)
    lines = list(result.actions)
    for note in result.needs_review:
        lines.append(f"needs review: {note}")
    if result.changes == 0:
        lines.append("update: nothing to do")
    else:
        lines.append(f"update: OK ({result.changes} changes)")
    return lines
