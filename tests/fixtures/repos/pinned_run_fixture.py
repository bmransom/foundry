"""Pinned-run migration fixture (T13): a conv-4, v1-layout git repo — vendored gate
scripts, a check-fast `.githooks/pre-push`, a CI gate step, and a manifest at
`conventionVersion` 4 — the input `m005_pinned_run.apply()` migrates.

Test-local only, never an eval target. Distinct from `doctor_fixture.py` (already
pinned, conv-agnostic) and `factory.py` (driver smoke) — this one carries the *old*
vendored layout a migration must consume.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

CHECK_FAST_PRE_PUSH = (
    "#!/usr/bin/env bash\n"
    "# foundry-template: pre-push v1\n"
    "# Pre-push gate; bypass once with `git push --no-verify`.\n"
    'exec "$(git rev-parse --show-toplevel)/scripts/check-fast.sh"\n'
)

CI_WORKFLOW = (
    "name: check-fast\n"
    "on:\n"
    "  push:\n"
    "    branches: [main]\n"
    "jobs:\n"
    "  gate:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/checkout@v4\n"
    "      - uses: astral-sh/setup-uv@v5\n"
    "      - run: scripts/check-fast.sh\n"
    "  docs-build:\n"
    "    runs-on: ubuntu-latest\n"
    "    steps:\n"
    "      - uses: actions/checkout@v4\n"
    "      - run: npm run build\n"
)

BOARD = (
    "# Fixture Roadmap\n\n"
    "| Id | Work | Status | Spec | Depends on |\n"
    "|---|---|---|---|---|\n"
    "| clean-card | Clean card | Ready | `roadmap/specs/clean-card/` | — |\n"
)

# The vendored v1 gate scripts. check-board.py + prose-lint.py are the gate suite's now;
# knowledge.py + check-fast.sh stay (knowledge.py's list/index subcommands remain in use).
_VENDORED = {
    "scripts/check-board.py": "#!/usr/bin/env python3\n# board check stub (suite owns this)\n",
    "scripts/prose-lint.py": "#!/usr/bin/env python3\n# prose lint stub (suite owns this)\n",
    "scripts/test_check_board.py": "# unit test for the deleted board script\n",
    "scripts/test_prose_lint.py": "# unit test for the deleted prose script\n",
    "scripts/knowledge.py": "#!/usr/bin/env python3\n# knowledge tool stub (kept: list/index)\n",
    "scripts/check-fast.sh": "#!/usr/bin/env bash\necho check-fast: PASS\n",
}

_IDENTITY = ("-c", "user.email=test@foundry", "-c", "user.name=Foundry Test")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_pinned_run_repo(root: Path) -> Path:
    """Build a conv-4 v1-layout repo at `root`, committed on `main`."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")

    _write(root / "roadmap" / "ROADMAP.md", BOARD)
    for rel, body in _VENDORED.items():
        _write(root / rel, body)
    pre_push = root / ".githooks" / "pre-push"
    _write(pre_push, CHECK_FAST_PRE_PUSH)
    pre_push.chmod(0o755)
    (root / "scripts" / "check-fast.sh").chmod(0o755)
    _write(root / ".github" / "workflows" / "check-fast.yml", CI_WORKFLOW)

    files: dict[str, dict] = {}
    for rel in (".githooks/pre-push", "scripts/check-board.py", "scripts/knowledge.py"):
        sha = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        files[rel] = {"template": Path(rel).stem, "version": 1, "sha256": sha}
    manifest = {
        "pluginVersion": "0.1.0",
        "conventionVersion": 4,
        "harnesses": ["claude-code"],
        "files": files,
    }
    _write(root / ".foundry" / "manifest.json", json.dumps(manifest, indent=2) + "\n")

    _git(root, *_IDENTITY, "add", "-A")
    _git(root, *_IDENTITY, "commit", "-qm", "init conv-4 fixture")
    return root
