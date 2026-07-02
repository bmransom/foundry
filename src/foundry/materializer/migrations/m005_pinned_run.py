"""Migration m005 — pinned run (convention 4 → 5, design D5/D6, AC-5.3).

Retires vendored gate scripts for the pinned `uvx ... foundry gate` command: rewrites
`.githooks/pre-push` and the CI gate step to it, writes `.foundry/config.toml` when
absent (preserving the repo's old gate command as a `[gate].commands` entry so nothing is
lost), deletes the gate-tool scripts the gate suite fully owns, and stamps
`conventionVersion` 5.

Deterministic and idempotent: `applies` keys on `conventionVersion == 4` plus a vendored
gate script or a check-fast pre-push — signals this migration removes — so a migrated repo
(conv 5) never re-triggers; `apply` re-run over a migrated tree writes nothing.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from foundry import __version__

CONVENTION = 5
DEFAULT_REPO_URL = "https://github.com/bmransom/foundry"

# Scripts the gate suite (foundry.gate.board / .prose) fully replaces — safe to delete.
# scripts/knowledge.py is NOT here: the suite ports only its `check`; its list/index/
# outline/section subcommands stay in use (README, rules, bootstrap).
_FULLY_OWNED = ("scripts/check-board.py", "scripts/prose-lint.py")
# The paired unit tests, orphaned once their script is gone.
_ORPHANED_TESTS = ("scripts/test_check_board.py", "scripts/test_prose_lint.py")

_MANIFEST_REL = ".foundry/manifest.json"
_PRE_PUSH_REL = ".githooks/pre-push"
_CONFIG_REL = ".foundry/config.toml"

# A repo gate script referenced by the old pre-push (e.g. scripts/check-fast.sh).
_GATE_SCRIPT_RE = re.compile(r"scripts/[\w.-]+\.sh")
# A CI `run:` step invoking the old gate script.
_CI_RUN_RE = re.compile(r"^(\s*-?\s*run:\s+).*check-fast\.sh.*$")


def _load_manifest(repo_root: Path) -> dict | None:
    path = repo_root / _MANIFEST_REL
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def applies(repo_root: Path | str) -> bool:
    repo_root = Path(repo_root)
    manifest = _load_manifest(repo_root)
    if not manifest or manifest.get("conventionVersion") != 4:
        return False
    vendored = any((repo_root / rel).is_file() for rel in _FULLY_OWNED)
    pre_push = repo_root / _PRE_PUSH_REL
    check_fast = pre_push.is_file() and "check-fast" in pre_push.read_text(encoding="utf-8")
    return vendored or check_fast


def _pinned_command(repo_url: str, pin: str) -> str:
    return f'uvx --from "git+{repo_url}@{pin}" foundry gate'


def apply(
    repo_root: Path | str,
    *,
    pin: str | None = None,
    repo_url: str = DEFAULT_REPO_URL,
) -> None:
    repo_root = Path(repo_root)
    pin = pin or ("v" + __version__)
    command = _pinned_command(repo_url, pin)

    pre_push = repo_root / _PRE_PUSH_REL
    old_pre_push = pre_push.read_text(encoding="utf-8") if pre_push.is_file() else ""
    match = _GATE_SCRIPT_RE.search(old_pre_push)
    repo_gate_command = match.group(0) if match else None

    _write_config(repo_root, pin, repo_url, repo_gate_command)
    _rewrite_pre_push(pre_push, command)
    _rewrite_ci(repo_root, command)
    deleted = _delete_owned_scripts(repo_root)
    _update_manifest(repo_root, pre_push, deleted)


def _write_config(repo_root: Path, pin: str, repo_url: str, gate_command: str | None) -> None:
    """Write `.foundry/config.toml` only when absent — never clobber a repo's own config."""
    path = repo_root / _CONFIG_REL
    if path.exists():
        return
    commands = f'["{gate_command}"]' if gate_command else "[]"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[foundry]\n"
        f'pin = "{pin}"\n'
        f'repo_url = "{repo_url}"\n\n'
        "[gate]\n"
        f"commands = {commands}\n",
        encoding="utf-8",
    )


def _rewrite_pre_push(pre_push: Path, command: str) -> None:
    pre_push.parent.mkdir(parents=True, exist_ok=True)
    pre_push.write_text(
        "#!/usr/bin/env bash\n"
        "# Pre-push gate; bypass once with `git push --no-verify`.\n"
        f"exec {command}\n",
        encoding="utf-8",
    )
    pre_push.chmod(0o755)


def _rewrite_ci(repo_root: Path, command: str) -> None:
    """Rewrite each CI `run:` step invoking the old gate script; keep every other step."""
    wf_dir = repo_root / ".github" / "workflows"
    if not wf_dir.is_dir():
        return
    workflows = sorted(wf_dir.glob("*.yml")) + sorted(wf_dir.glob("*.yaml"))
    for wf in workflows:
        text = wf.read_text(encoding="utf-8")
        lines = text.split("\n")
        changed = False
        for i, line in enumerate(lines):
            match = _CI_RUN_RE.match(line)
            if match:
                lines[i] = f"{match.group(1)}{command}"
                changed = True
        if changed:
            wf.write_text("\n".join(lines), encoding="utf-8")


def _delete_owned_scripts(repo_root: Path) -> list[str]:
    deleted: list[str] = []
    for rel in (*_FULLY_OWNED, *_ORPHANED_TESTS):
        path = repo_root / rel
        if path.is_file():
            path.unlink()
            deleted.append(rel)
    return deleted


def _update_manifest(repo_root: Path, pre_push: Path, deleted: list[str]) -> None:
    path = repo_root / _MANIFEST_REL
    if not path.is_file():
        return
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["conventionVersion"] = CONVENTION
    files = manifest.get("files", {})
    for rel in deleted:
        files.pop(rel, None)
    entry = files.get(_PRE_PUSH_REL)
    if entry is not None and pre_push.is_file():
        entry["sha256"] = hashlib.sha256(pre_push.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
