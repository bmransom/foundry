"""Sandbox helper for eval flows that mutate git config.

The recorded corruption flipped `core.bare` to true and overwrote `[user]` in
the real repo's `.git/config` during a concurrent eval run. Linked worktrees
share `.git/config`, so worktree isolation alone does not close this class. The
rule: every eval entrypoint or flow that mutates git config — shell or Python —
operates on a clone or copy of the repo, never the real repo.

Use `sandbox_repo` to get an isolated copy with its own `.git/config`; mutate
that. Use `guard_real_config` in a flow or test driver to assert the real repo's
`.git/config` is byte-identical before and after a run.
"""

from __future__ import annotations

import contextlib
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from pathlib import Path


def _has_git_dir(repo_root: Path) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--git-dir"],
            capture_output=True,
        ).returncode
        == 0
    )


@contextlib.contextmanager
def sandbox_repo(repo_root: Path | str) -> Iterator[Path]:
    """Yield an isolated copy of the repo with its OWN .git/config.

    A `git clone --local` gives the copy a separate `.git/config`, so config
    mutations on the copy never reach the source. Falls back to a directory copy
    when the source is not a git repo. The sandbox is removed on exit.
    """
    source = Path(repo_root).resolve()
    sandbox_parent = Path(tempfile.mkdtemp(prefix="foundry-eval-sandbox-"))
    sandbox = sandbox_parent / "repo"
    try:
        if _has_git_dir(source):
            subprocess.run(
                ["git", "clone", "--quiet", "--local", str(source), str(sandbox)],
                check=True,
                capture_output=True,
            )
        else:
            shutil.copytree(source, sandbox)
        yield sandbox
    finally:
        shutil.rmtree(sandbox_parent, ignore_errors=True)


class RealConfigMutated(AssertionError):
    """Raised when a flow mutated the real repo's .git/config."""


@contextlib.contextmanager
def guard_real_config(repo_root: Path | str) -> Iterator[None]:
    """Assert the real repo's .git/config is byte-identical before and after.

    Wrap a config-mutating flow in this guard in a flow or test driver: if the
    flow writes the real `.git/config` (the recorded failure mode), the guard
    raises RealConfigMutated, even when the flow itself exits cleanly.
    """
    config_path = Path(repo_root).resolve() / ".git" / "config"
    before = config_path.read_bytes() if config_path.exists() else None
    try:
        yield
    finally:
        after = config_path.read_bytes() if config_path.exists() else None
        if before != after:
            raise RealConfigMutated(
                f"{config_path} changed during the run — a config-mutating eval "
                f"flow must operate on a sandbox copy, never the real repo"
            )
