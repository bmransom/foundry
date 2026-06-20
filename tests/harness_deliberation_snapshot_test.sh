#!/usr/bin/env bash
# Unit checks for portable harness-deliberation snapshot capture.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$BROKER" ] || fail "missing broker script"

fixture_root="$(mktemp -d)"
trap 'rm -rf "$fixture_root"' EXIT

python3 - "$BROKER" "$fixture_root" <<'PY'
import importlib.util
import json
import pathlib
import subprocess
import sys

broker_path = pathlib.Path(sys.argv[1])
fixture_root = pathlib.Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("harness_deliberation_broker", broker_path)
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)


def run(command, cwd=None):
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


repo = fixture_root / "repo"
repo.mkdir()
run(["git", "init", "-b", "main"], cwd=repo)
run(["git", "config", "user.email", "foundry@example.test"], cwd=repo)
run(["git", "config", "user.name", "Foundry Test"], cwd=repo)
(repo / ".gitignore").write_text(".foundry/tmp/\n", encoding="utf-8")
(repo / "README.md").write_text("base\n", encoding="utf-8")
run(["git", "add", ".gitignore", "README.md"], cwd=repo)
run(["git", "commit", "-m", "initial"], cwd=repo)
base_commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo)

session_dir = repo / ".foundry/tmp/harness-deliberation/snapshot-demo"
broker.SessionStore.create(
    session_dir=session_dir,
    session_id="snapshot-demo",
    repo_root=repo,
    base_commit=base_commit,
    participants=["codex", "claude-code"],
    config={"stall_rounds": 2},
)
worktrees = broker.create_scratch_worktrees(session_dir=session_dir)
codex_path = pathlib.Path(next(item["path"] for item in worktrees if item["actor"] == "codex"))

(codex_path / "README.md").write_text("base\ntracked change\n", encoding="utf-8")
(codex_path / "notes").mkdir()
(codex_path / "notes/new.md").write_text("untracked note\n", encoding="utf-8")
(codex_path / "asset.bin").write_bytes(b"\x00foundry\xff")

snapshot = broker.capture_snapshot(session_dir=session_dir, actor="codex")
assert_equal(snapshot["snapshot_id"], "0001-codex", "snapshot id")
assert_equal(snapshot["actor"], "codex", "snapshot actor")
assert_equal(snapshot["base_commit"], base_commit, "snapshot base commit")
assert snapshot["complete"], "snapshot is complete"
record_path = session_dir / snapshot["snapshot_record_path"]
assert_equal(snapshot["snapshot_record_path"], "snapshots/0001-codex/snapshot.json", "snapshot record path")
record = json.loads(record_path.read_text(encoding="utf-8"))
assert_equal(record["tracked_diff"]["path"], "snapshots/0001-codex/tracked.diff", "tracked diff path")
assert_equal(
    [item["path"] for item in record["untracked"]],
    ["asset.bin", "notes/new.md"],
    "untracked-file index order",
)
for item in record["untracked"]:
    assert (session_dir / item["payload_path"]).is_file(), f"missing payload {item['payload_path']}"
    assert item["bytes"] > 0, "byte count recorded"
    assert len(item["sha256"]) == 64, "hash recorded"

events = [
    json.loads(line)
    for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal(events[-1]["type"], "snapshot", "snapshot event type")
assert_equal(
    events[-1]["payloads"]["snapshot_record"]["path"],
    snapshot["snapshot_record_path"],
    "snapshot event record payload",
)

run(["git", "-C", str(repo), "worktree", "remove", "--force", str(codex_path)])
assert not codex_path.exists(), "scratch worktree removed"

reconstructed = fixture_root / "reconstructed"
broker.reconstruct_snapshot(
    session_dir=session_dir,
    snapshot_id="0001-codex",
    output_dir=reconstructed,
)
assert_equal((reconstructed / "README.md").read_text(encoding="utf-8"), "base\ntracked change\n", "tracked diff reconstructed")
assert_equal((reconstructed / "notes/new.md").read_text(encoding="utf-8"), "untracked note\n", "untracked text reconstructed")
assert_equal((reconstructed / "asset.bin").read_bytes(), b"\x00foundry\xff", "untracked binary reconstructed")
PY

echo "harness_deliberation_snapshot_test: PASS"
