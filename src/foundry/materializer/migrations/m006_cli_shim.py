"""Migration m006 — cli shim (convention 5 → 6).

Installs the repo-local `.foundry/bin/foundry` shim and collapses the pin: the pre-push
hook and CI gate step move from a hardcoded `uvx --from "git+<repo>@<pin>" foundry gate`
to `.foundry/bin/foundry gate`, so the pinned tag lives only in `.foundry/config.toml`.
The shim reads the pin at run time (self-host-aware — the local tree in foundry's own repo).

Deterministic and idempotent: `applies` keys on `conventionVersion == 5` plus the shim's
absence — the structural signal this migration removes — so a migrated repo (conv 6, shim
present) never re-triggers.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from foundry.materializer.bootstrap import verbatim_root

CONVENTION = 6
ID = "cli-shim"

_MANIFEST_REL = ".foundry/manifest.json"
_SHIM_REL = ".foundry/bin/foundry"
_PRE_PUSH_REL = ".githooks/pre-push"

# The hardcoded pinned gate command this migration replaces (m005's form).
_UVX_GATE_RE = re.compile(r'uvx --from "git\+[^"]+@[^"]+" foundry gate')
_SHIM_GATE = ".foundry/bin/foundry gate"


def _load_manifest(repo_root: Path) -> dict | None:
    path = repo_root / _MANIFEST_REL
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def applies(repo_root: Path | str) -> bool:
    repo_root = Path(repo_root)
    manifest = _load_manifest(repo_root)
    if not manifest or manifest.get("conventionVersion") != 5:
        return False
    return not (repo_root / _SHIM_REL).is_file()


def _install_shim(repo_root: Path) -> str | None:
    """Copy the verbatim shim into the repo, executable. Returns its sha256, or None if
    the package template is missing (never, in a real install)."""
    source = verbatim_root() / _SHIM_REL
    if not source.is_file():
        return None
    dest = repo_root / _SHIM_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    content = source.read_bytes()
    dest.write_bytes(content)
    dest.chmod(0o755)
    return hashlib.sha256(content).hexdigest()


def _collapse_pin(text: str) -> tuple[str, bool]:
    """Rewrite the hardcoded pinned gate command to the pin-free shim call."""
    new = _UVX_GATE_RE.sub(_SHIM_GATE, text)
    return new, new != text


def _rewrite_ci(repo_root: Path) -> None:
    wf_dir = repo_root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return
    for wf in sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml")):
        new, changed = _collapse_pin(wf.read_text(encoding="utf-8"))
        if changed:
            wf.write_text(new, encoding="utf-8")


def apply(repo_root: Path | str) -> None:
    repo_root = Path(repo_root)
    shim_hash = _install_shim(repo_root)

    pre_push = repo_root / _PRE_PUSH_REL
    if pre_push.is_file():
        new, changed = _collapse_pin(pre_push.read_text(encoding="utf-8"))
        if changed:
            pre_push.write_text(new, encoding="utf-8")

    _rewrite_ci(repo_root)
    _update_manifest(repo_root, shim_hash)


def _update_manifest(repo_root: Path, shim_hash: str | None) -> None:
    path = repo_root / _MANIFEST_REL
    if not path.is_file():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["conventionVersion"] = CONVENTION
    files = manifest.get("files", {})
    if shim_hash is not None:
        files[_SHIM_REL] = {"template": "foundry-shim", "version": 1, "sha256": shim_hash}
    pre_push = repo_root / _PRE_PUSH_REL
    entry = files.get(_PRE_PUSH_REL)
    if entry is not None and pre_push.is_file():
        entry["sha256"] = hashlib.sha256(pre_push.read_bytes()).hexdigest()
    manifest["files"] = dict(sorted(files.items()))
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
