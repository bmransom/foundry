"""Doctor fixture builder (T12): a minimal git repo carrying `.foundry/config.toml`,
`.foundry/manifest.json`, `.githooks/pre-push`, and `roadmap/ROADMAP.md`, with one
knob per doctor check so a discrimination test can seed exactly one defect.

Distinct from `tests/fixtures/repos/factory.py` (T7's driver fixture, pinned to
"v2.0.0" for a different purpose) and `gate_fixture.py` (gate-suite only, no git/hooks
state) — doctor needs git config (hooksPath) and a version-matching pin, neither of
which the other two builders provide.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

from foundry import __version__

CLEAN_BOARD = (
    "# Fixture Roadmap\n\n"
    "| Id | Work | Status | Spec | Depends on |\n"
    "|---|---|---|---|---|\n"
    "| clean-card | Clean card | Ready | `roadmap/specs/clean-card/` | — |\n"
)

BROKEN_BOARD = (
    "# Fixture Roadmap\n\n"
    "| Id | Work | Status | Spec | Depends on |\n"
    "|---|---|---|---|---|\n"
    "|  | New feature | Ready | `roadmap/specs/new-feature/` | — |\n"
)

PINNED_GATE_PRE_PUSH = (
    "#!/usr/bin/env bash\n"
    'exec uvx --from "git+https://github.com/bmransom/foundry@v2.0.0" foundry gate\n'
)

CHECK_FAST_PRE_PUSH = (
    "#!/usr/bin/env bash\n"
    'exec "$(git rev-parse --show-toplevel)/scripts/check-fast.sh"\n'
)

NEITHER_PRE_PUSH = "#!/usr/bin/env bash\necho hi\n"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_doctor_repo(
    root: Path,
    *,
    config_malformed: bool = False,
    pin: str | None = __version__,
    routing_harness: str = "claude-code",
    manifest_present: bool = True,
    manifest_harnesses: list[str] | None = None,
    manifest_hash_defect: bool = False,
    hooks_path_set: bool = True,
    pre_push_text: str | None = PINNED_GATE_PRE_PUSH,
    board_text: str = CLEAN_BOARD,
) -> Path:
    """Build a clean-by-default doctor fixture; pass one non-default kwarg per test
    to seed exactly one defect. `root` need not exist yet.
    """
    root = Path(root)
    _git(root, "init", "-q", "-b", "main")

    _write(root / "roadmap" / "ROADMAP.md", board_text)

    if config_malformed:
        _write(root / ".foundry" / "config.toml", "[foundry\npin = broken\n")
    else:
        pin_line = f'pin = "{pin}"\n' if pin is not None else ""
        _write(
            root / ".foundry" / "config.toml",
            f"[foundry]\n{pin_line}\n"
            f"[routing.default]\nharness = \"{routing_harness}\"\n",
        )

    if manifest_present:
        harnesses = manifest_harnesses if manifest_harnesses is not None else [routing_harness]
        roadmap_path = root / "roadmap" / "ROADMAP.md"
        digest = hashlib.sha256(roadmap_path.read_bytes()).hexdigest()
        if manifest_hash_defect:
            digest = "0" * 64
        manifest = {
            "harnesses": harnesses,
            "files": {
                "roadmap/ROADMAP.md": {"template": "roadmap", "version": 1, "sha256": digest},
            },
        }
        _write(root / ".foundry" / "manifest.json", json.dumps(manifest))

    if pre_push_text is not None:
        pre_push = root / ".githooks" / "pre-push"
        _write(pre_push, pre_push_text)
        pre_push.chmod(0o755)

    if hooks_path_set:
        _git(root, "config", "core.hooksPath", ".githooks")

    return root
