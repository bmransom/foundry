"""m006_cli_shim (conv 5→6): install `.foundry/bin/foundry` and collapse the pin — the
pre-push hook and CI move from a hardcoded `uvx` pin to the pin-free shim call, leaving the
pinned tag only in `.foundry/config.toml`. `applies` keys on the shim's absence (idempotent).
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from foundry.materializer.migrations import m006_cli_shim as m

_PINNED = 'uvx --from "git+https://github.com/x/foundry@v0.2.4" foundry gate'


def _conv5_repo(root: Path) -> Path:
    (root / ".githooks").mkdir(parents=True)
    (root / ".githooks" / "pre-push").write_text(
        "#!/usr/bin/env bash\n"
        "# Pre-push gate; bypass once with `git push --no-verify`.\n"
        f"exec {_PINNED}\n",
        encoding="utf-8",
    )
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "gate.yml").write_text(
        f"jobs:\n  gate:\n    steps:\n      - run: {_PINNED}\n", encoding="utf-8"
    )
    (root / ".foundry").mkdir()
    (root / ".foundry" / "config.toml").write_text(
        '[foundry]\npin = "v0.2.4"\nrepo_url = "https://github.com/x/foundry"\n\n'
        "[gate]\ncommands = []\n",
        encoding="utf-8",
    )
    (root / ".foundry" / "manifest.json").write_text(
        json.dumps(
            {
                "pluginVersion": "0.2.4",
                "conventionVersion": 5,
                "harnesses": ["claude-code"],
                "files": {
                    ".githooks/pre-push": {
                        "template": "pre-push", "version": 1, "sha256": "stale",
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return root


def test_applies_on_conv5_without_shim(tmp_path):
    assert m.applies(_conv5_repo(tmp_path / "r")) is True


def test_apply_installs_executable_shim(tmp_path):
    repo = _conv5_repo(tmp_path / "r")
    m.apply(repo)
    shim = repo / ".foundry" / "bin" / "foundry"
    assert shim.is_file()
    assert os.access(shim, os.X_OK)


def test_apply_collapses_pin_in_hook_and_ci(tmp_path):
    repo = _conv5_repo(tmp_path / "r")
    m.apply(repo)
    hook = (repo / ".githooks" / "pre-push").read_text()
    assert "exec .foundry/bin/foundry gate" in hook and "uvx --from" not in hook
    ci = (repo / ".github" / "workflows" / "gate.yml").read_text()
    assert ".foundry/bin/foundry gate" in ci and "uvx --from" not in ci
    # the pinned tag survives only in config.toml
    assert 'pin = "v0.2.4"' in (repo / ".foundry" / "config.toml").read_text()


def test_apply_stamps_convention_6_and_tracks_shim(tmp_path):
    repo = _conv5_repo(tmp_path / "r")
    m.apply(repo)
    manifest = json.loads((repo / ".foundry" / "manifest.json").read_text())
    assert manifest["conventionVersion"] == 6
    entry = manifest["files"][".foundry/bin/foundry"]
    disk = hashlib.sha256((repo / ".foundry" / "bin" / "foundry").read_bytes()).hexdigest()
    assert entry["sha256"] == disk and entry["template"] == "foundry-shim"


def test_applies_false_after_migration(tmp_path):
    repo = _conv5_repo(tmp_path / "r")
    m.apply(repo)
    assert m.applies(repo) is False


def test_apply_is_idempotent(tmp_path):
    repo = _conv5_repo(tmp_path / "r")
    m.apply(repo)
    hook = (repo / ".githooks" / "pre-push").read_text()
    m.apply(repo)  # a direct re-run must not double-rewrite
    assert (repo / ".githooks" / "pre-push").read_text() == hook
