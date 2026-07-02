"""Migration + update fixtures (T16a): old-layout repos each migration/update consumes.

Pure-filesystem builders (no git — the materializer's migrations and update engine are
plain file operations). Test-local only, never eval targets. Each builder returns the
repo root it wrote.

- `make_okf_repo`      — conv-1 `docs/` layout (m002 input).
- `make_harness_repo`  — conv-2 `.claude/rules/` layout (m003 input).
- `make_card_ids_repo` — conv-3 board without an `Id` column (m004 input).
- `make_conv1_chain_repo` — a full conv-1 layout that updates 1→5 through every module.
- `make_legacy_repo`   — verbatim files but no manifest (update's legacy backfill input).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def _write(path: Path, text: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- shared content ------------------------------------------------------------------

GLOSSARY_KIND = (
    "---\n"
    "title: Glossary\n"
    "description: the terms\n"
    "kind: reference\n"
    "---\n\n"
    "# Glossary\n\nbody\n"
)
ARCH_KIND = (
    "---\n"
    "title: Architecture\n"
    "description: how it fits\n"
    "kind: architecture\n"
    "---\n\n"
    "# Architecture\n"
)
ORPHAN_NO_KIND = (
    "---\n"
    "title: Orphan\n"
    "description: a concept with no kind field\n"
    "---\n\n"
    "# Orphan\n"
)
DOCS_CONFIG = json.dumps(
    {
        "index_title": "My Docs",
        "kinds": ["reference", "architecture"],
        "doc_globs": ["docs/*.md"],
        "exclude_paths": ["docs/index.md"],
        "lifecycles": ["current"],
        "required_fields": ["title", "description", "kind"],
    },
    indent=2,
) + "\n"

BOARD_NO_ID = (
    "# Roadmap\n\n"
    "## Status Dashboard\n\n"
    "| Work | Status | Spec | Depends on |\n"
    "|---|---|---|---|\n"
    "| Paste command | Ready | `specs/paste/` | — |\n"
    "| Copy command | Backlog | `specs/copy/` | — |\n"
    "| Paste command | In progress | `specs/paste2/` | — |\n"
)

CHECK_FAST = "#!/usr/bin/env bash\npython3 scripts/docs.py check\necho check-fast: PASS\n"
CHECK_FAST_PRE_PUSH = (
    "#!/usr/bin/env bash\n"
    "# foundry-template: pre-push v1\n"
    "# Pre-push gate; bypass once with `git push --no-verify`.\n"
    'exec "$(git rev-parse --show-toplevel)/scripts/check-fast.sh"\n'
)
DOCS_PY = "#!/usr/bin/env python3\n# foundry-template: docs v1\n# old docs tool\n"
TEST_DOCS_PY = "# foundry-template: test-docs v1\n# old docs tool test\n"

RULE_SPEC = (
    "---\npaths:\n  - \"roadmap/specs/**/*.md\"\n---\n\n"
    "<!-- foundry-seed: spec-conventions v1 -->\n\n# Spec conventions\n"
)


def _legacy_manifest(root: Path, tracked: dict[str, dict], *, convention: int | None) -> dict:
    manifest: dict = {"pluginVersion": "0.1.0", "files": tracked}
    if convention is not None:
        manifest["conventionVersion"] = convention
    return manifest


# --- builders ------------------------------------------------------------------------


def make_okf_repo(root: Path) -> Path:
    """conv-1 `docs/` layout with a legacy top-level `.foundry-manifest.json`."""
    root = Path(root)
    _write(root / "docs" / "glossary.md", GLOSSARY_KIND)
    _write(root / "docs" / "architecture.md", ARCH_KIND)
    _write(root / "docs" / "orphan.md", ORPHAN_NO_KIND)
    _write(root / "docs" / "ROADMAP.md", BOARD_NO_ID)
    _write(root / "docs" / "BACKLOG.md", "---\nkind: reference\n---\n\n# Backlog\n")
    _write(root / "docs" / "docs-config.json", DOCS_CONFIG)
    _write(root / "docs" / ".vitepress" / "config.ts", "// old vitepress config\n")
    _write(root / "docs" / "package.json", '{"name": "docs"}\n')
    _write(root / "specs" / "feature-x" / "design.md", "# design\n")
    _write(root / "scripts" / "docs.py", DOCS_PY, executable=True)
    _write(root / "scripts" / "test_docs.py", TEST_DOCS_PY)
    _write(root / "scripts" / "check-fast.sh", CHECK_FAST, executable=True)
    _write(root / "AGENTS.md", "See docs/glossary.md and specs/ for detail.\n")

    tracked = {
        "scripts/docs.py": {
            "template": "docs", "version": 1, "sha256": _sha(root / "scripts" / "docs.py")
        },
        "scripts/test_docs.py": {
            "template": "test-docs", "version": 1,
            "sha256": _sha(root / "scripts" / "test_docs.py"),
        },
    }
    manifest = _legacy_manifest(root, tracked, convention=None)
    _write(root / ".foundry-manifest.json", json.dumps(manifest, indent=2) + "\n")
    return root


def make_harness_repo(root: Path) -> Path:
    """conv-2 layout: `.claude/rules/` + a top-level `.foundry-manifest.json`."""
    root = Path(root)
    _write(root / "knowledge" / "glossary.md",
           "---\ntitle: Glossary\ndescription: terms\ntype: reference\n---\n\n# Glossary\n")
    _write(root / ".claude" / "rules" / "spec-conventions.md", RULE_SPEC)
    _write(root / ".claude" / "rules" / "knowledge-conventions.md",
           "<!-- foundry-seed: knowledge-conventions v1 -->\n\n# Knowledge conventions\n")
    _write(root / "CLAUDE.md", "# Agents\nSee .claude/rules/ for the rules.\n")
    _write(root / "AGENTS.md", "Rules live in .claude/rules/.\n")
    _write(root / "scripts" / "check-fast.sh",
           "#!/usr/bin/env bash\nls .claude/rules/\n", executable=True)

    manifest = _legacy_manifest(root, {}, convention=2)
    _write(root / ".foundry-manifest.json", json.dumps(manifest, indent=2) + "\n")
    return root


def make_card_ids_repo(root: Path) -> Path:
    """conv-3 layout: a board whose card-table header has no `Id` column."""
    root = Path(root)
    _write(root / "roadmap" / "ROADMAP.md", BOARD_NO_ID)
    manifest = _legacy_manifest(root, {}, convention=3)
    _write(root / ".foundry" / "manifest.json", json.dumps(manifest, indent=2) + "\n")
    return root


def make_conv1_chain_repo(root: Path) -> Path:
    """A full conv-1 layout carrying every old-convention signal, so `foundry update`
    walks it 1→5 through m002…m005 in order."""
    root = Path(root)
    _write(root / "docs" / "glossary.md", GLOSSARY_KIND)
    _write(root / "docs" / "notes.md", ORPHAN_NO_KIND)
    _write(root / "docs" / "ROADMAP.md", BOARD_NO_ID)
    _write(root / "docs" / "docs-config.json", DOCS_CONFIG)
    _write(root / "specs" / "feat" / "design.md", "# design\n")
    _write(root / "scripts" / "docs.py", DOCS_PY, executable=True)
    _write(root / "scripts" / "check-fast.sh", CHECK_FAST, executable=True)
    _write(root / ".claude" / "rules" / "spec-conventions.md", RULE_SPEC)
    _write(root / "CLAUDE.md", "# Agents\n")
    pre_push = root / ".githooks" / "pre-push"
    _write(pre_push, CHECK_FAST_PRE_PUSH, executable=True)

    tracked = {
        "scripts/docs.py": {
            "template": "docs", "version": 1, "sha256": _sha(root / "scripts" / "docs.py")
        },
    }
    manifest = _legacy_manifest(root, tracked, convention=None)
    _write(root / ".foundry-manifest.json", json.dumps(manifest, indent=2) + "\n")
    return root


def make_legacy_repo(root: Path) -> Path:
    """A repo with a pristine tracked verbatim file and a customized one but NO manifest —
    the update engine must backfill a manifest from `foundry-template:` markers, recording
    the pristine file and flagging the customized one for review (never overwriting it)."""
    from foundry.materializer.bootstrap import verbatim_root

    root = Path(root)
    vroot = verbatim_root()
    # Pristine: byte-exact copy of the shipped worktree-retire template.
    pristine_rel = "scripts/worktree-retire.sh"
    _write(root / pristine_rel, (vroot / pristine_rel).read_text(encoding="utf-8"),
           executable=True)
    # Customized: the board template with a local edit (marker kept).
    board_rel = "scripts/board.sh"
    board = (vroot / board_rel).read_text(encoding="utf-8")
    _write(root / board_rel, board + "\n# local customization\n", executable=True)
    # A modern board so no migration fires — this is a pure backfill+refresh case.
    _write(root / "roadmap" / "ROADMAP.md",
           "# Roadmap\n\n| Id | Work | Status | Spec | Depends on |\n"
           "|---|---|---|---|---|\n| c1 | Card | Ready | `roadmap/specs/c1/` | — |\n")
    return root
