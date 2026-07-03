"""`foundry update` (AC-7.3): legacy backfill, hash-compare (refresh pristine-outdated,
flag customized never-overwrite), migration chain from the repo's convention to head,
restamp, idempotency, and dry-run. The 1→5 chain proves every migration module runs in
order over a conv-1-layout fixture.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from foundry import __version__
from foundry.materializer import update as u
from foundry.materializer.bootstrap import verbatim_root


def _manifest(repo):
    for rel in (".foundry/manifest.json", ".foundry-manifest.json"):
        p = repo / rel
        if p.is_file():
            return json.loads(p.read_text())
    raise AssertionError("no manifest")


# --- legacy backfill -----------------------------------------------------------------


def test_backfills_missing_manifest(tmp_path, legacy_fixture):
    repo = legacy_fixture(tmp_path / "r")
    assert not (repo / ".foundry" / "manifest.json").exists()
    result = u.update(repo)
    assert result.backfilled is True
    manifest = _manifest(repo)
    assert "scripts/worktree-retire.sh" in manifest["files"]


def test_backfill_flags_customized_never_overwrites(tmp_path, legacy_fixture):
    repo = legacy_fixture(tmp_path / "r")
    before = (repo / "scripts" / "board.sh").read_text()
    result = u.update(repo)
    # The locally-edited board.sh is left byte-identical and reported, never refreshed.
    assert (repo / "scripts" / "board.sh").read_text() == before
    assert "scripts/board.sh" in result.customized


# --- hash-compare refresh ------------------------------------------------------------


def test_refreshes_pristine_outdated(tmp_path):
    repo = tmp_path / "r"
    vroot = verbatim_root()
    rel = "scripts/worktree-retire.sh"
    content = (vroot / rel).read_bytes()
    (repo / "scripts").mkdir(parents=True)
    (repo / rel).write_bytes(content)
    marker_version = _marker_version(content.decode())
    # Manifest tracks it one version behind, but the on-disk hash is pristine.
    (repo / ".foundry").mkdir()
    manifest = {
        "pluginVersion": "0.0.1",
        "conventionVersion": u.HEAD,
        "harnesses": ["claude-code"],
        "files": {
            rel: {
                "template": "worktree-retire",
                "version": marker_version - 1,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        },
    }
    (repo / ".foundry" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    result = u.update(repo)
    assert rel in result.refreshed
    entry = _manifest(repo)["files"][rel]
    assert entry["version"] == marker_version
    assert (repo / rel).read_bytes() == content


def _marker_version(text):
    import re

    return int(re.search(r"foundry-template:\s*\S+\s+v(\d+)", text).group(1))


# --- migration chain 1 → 5 -----------------------------------------------------------


def test_chain_conv1_to_5(tmp_path, conv1_chain_fixture):
    repo = conv1_chain_fixture(tmp_path / "r")
    result = u.update(repo)

    manifest = _manifest(repo)
    assert manifest["conventionVersion"] == 5
    assert manifest["pluginVersion"] == __version__
    # m002: docs → knowledge, kind→type.
    assert (repo / "knowledge" / "glossary.md").is_file()
    assert not (repo / "docs").exists()
    # m003: rules moved, manifest relocated, harness set recorded.
    assert (repo / "rules" / "spec-conventions.md").is_file()
    assert (repo / ".foundry" / "manifest.json").is_file()
    assert manifest["harnesses"] == ["claude-code"]
    # m004: board gained an Id column with a filled claimable card.
    board = (repo / "roadmap" / "ROADMAP.md").read_text()
    assert "| Id |" in board
    assert "| paste-command |" in board
    # m005: pinned run command in the pre-push, conv stamped 5.
    pre_push = (repo / ".githooks" / "pre-push").read_text()
    assert "foundry gate" in pre_push and "check-fast" not in pre_push
    assert set(result.migrated) == {
        "okf-knowledge", "harness-agnostic", "card-ids", "pinned-run"
    }


def test_chain_second_run_nothing_to_do(tmp_path, conv1_chain_fixture):
    repo = conv1_chain_fixture(tmp_path / "r")
    u.update(repo)
    result = u.update(repo)
    assert result.changes == 0
    assert result.migrated == []


# --- dry run -------------------------------------------------------------------------


def test_dry_run_writes_nothing(tmp_path, conv1_chain_fixture):
    repo = conv1_chain_fixture(tmp_path / "r")
    result = u.update(repo, dry_run=True)
    assert (repo / "docs").exists()  # untouched
    assert not (repo / "knowledge").exists()
    assert result.changes > 0  # a plan was produced
    assert any("would" in line.lower() for line in result.actions)


# --- CLI -----------------------------------------------------------------------------


def test_cli_reports_changes(tmp_path, conv1_chain_fixture, monkeypatch, capsys):
    from foundry.cli import main

    repo = conv1_chain_fixture(tmp_path / "r")
    monkeypatch.chdir(repo)
    rc = main(["update"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip().splitlines()[-1].startswith("update: OK (")


def test_cli_nothing_to_do(tmp_path, conv1_chain_fixture, monkeypatch, capsys):
    from foundry.cli import main

    repo = conv1_chain_fixture(tmp_path / "r")
    monkeypatch.chdir(repo)
    main(["update"])
    capsys.readouterr()
    rc = main(["update"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.strip().splitlines()[-1] == "update: nothing to do"


def test_cli_dry_run(tmp_path, conv1_chain_fixture, monkeypatch, capsys):
    from foundry.cli import main

    repo = conv1_chain_fixture(tmp_path / "r")
    monkeypatch.chdir(repo)
    rc = main(["update", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert (repo / "docs").exists()  # nothing written
    assert "would" in out.lower()


# --- knowledge index regeneration on template refresh (update-index-regen) ------------


def _knowledge_repo_with_stale_index(tmp_path):
    """A repo whose knowledge.py is manifest-tracked one version behind (pristine
    bytes) with a knowledge base whose index.md the refreshed script must regenerate."""
    repo = tmp_path / "r"
    vroot = verbatim_root()
    rel = "scripts/knowledge.py"
    content = (vroot / rel).read_bytes()
    (repo / "scripts").mkdir(parents=True)
    (repo / rel).write_bytes(content)
    marker_version = _marker_version(content.decode())

    seeds = Path(str(vroot)).parent / "seeds"
    (repo / "knowledge").mkdir()
    (repo / "knowledge" / "knowledge-config.json").write_bytes(
        (seeds / "knowledge" / "knowledge-config.json").read_bytes()
    )
    (repo / "knowledge" / "demo.md").write_text(
        "---\ntitle: Demo concept\ndescription: A demo.\ntype: reference\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    (repo / "knowledge" / "index.md").write_text("STALE-INDEX\n", encoding="utf-8")

    (repo / ".foundry").mkdir()
    manifest = {
        "pluginVersion": "0.0.1",
        "conventionVersion": u.HEAD,
        "harnesses": ["claude-code"],
        "files": {
            rel: {
                "template": "knowledge",
                "version": marker_version - 1,
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        },
    }
    (repo / ".foundry" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return repo


def test_refreshing_knowledge_template_regenerates_the_index(tmp_path):
    repo = _knowledge_repo_with_stale_index(tmp_path)
    result = u.update(repo)
    assert "scripts/knowledge.py" in result.refreshed
    assert any("regenerate knowledge/index.md" in a and not a.startswith("would") for a in result.actions)
    index = (repo / "knowledge" / "index.md").read_text(encoding="utf-8")
    assert "STALE-INDEX" not in index
    assert "Demo concept" in index


def test_dry_run_would_regenerate_without_writing(tmp_path):
    repo = _knowledge_repo_with_stale_index(tmp_path)
    result = u.update(repo, dry_run=True)
    assert any(a == "would regenerate knowledge/index.md" for a in result.actions)
    assert (repo / "knowledge" / "index.md").read_text(encoding="utf-8") == "STALE-INDEX\n"


def test_no_knowledge_refresh_means_no_regeneration(tmp_path):
    repo = _knowledge_repo_with_stale_index(tmp_path)
    # Bring the manifest up to the current version: nothing to refresh.
    manifest = _manifest(repo)
    manifest["files"]["scripts/knowledge.py"]["version"] = _marker_version(
        (verbatim_root() / "scripts/knowledge.py").read_text()
    )
    (repo / ".foundry" / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    result = u.update(repo)
    assert not any("regenerate" in a for a in result.actions)
    assert (repo / "knowledge" / "index.md").read_text(encoding="utf-8") == "STALE-INDEX\n"
