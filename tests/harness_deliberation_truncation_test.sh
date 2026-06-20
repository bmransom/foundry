#!/usr/bin/env bash
# Unit checks for snapshot byte ceiling and incomplete snapshot behavior.
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

session_dir = repo / ".foundry/tmp/harness-deliberation/truncation-demo"
broker.SessionStore.create(
    session_dir=session_dir,
    session_id="truncation-demo",
    repo_root=repo,
    base_commit=base_commit,
    participants=["codex", "claude-code"],
    config={"stall_rounds": 2},
)
worktrees = broker.create_scratch_worktrees(session_dir=session_dir)
codex_path = pathlib.Path(next(item["path"] for item in worktrees if item["actor"] == "codex"))
(codex_path / "small.txt").write_text("small", encoding="utf-8")
(codex_path / "large.txt").write_text("this file exceeds the ceiling\n", encoding="utf-8")

snapshot = broker.capture_snapshot(session_dir=session_dir, actor="codex", byte_ceiling=8)
assert_equal(snapshot["snapshot_id"], "0001-codex", "snapshot id")
assert_equal(snapshot["complete"], False, "snapshot is incomplete")

record = json.loads((session_dir / snapshot["snapshot_record_path"]).read_text(encoding="utf-8"))
assert_equal(snapshot["snapshot_record_path"], "snapshots/0001-codex/snapshot.json", "snapshot record path")
assert_equal(record["complete"], False, "snapshot record incomplete")
assert_equal(record["byte_ceiling"], 8, "snapshot record byte ceiling")
entries = {item["path"]: item for item in record["untracked"]}
assert_equal(entries["small.txt"]["captured"], True, "small file captured")
assert_equal(entries["large.txt"]["captured"], False, "large file omitted")
assert "payload_path" not in entries["large.txt"], "omitted file has no payload path"
assert_equal(record["omitted_bytes"], len(b"this file exceeds the ceiling\n"), "omitted byte count")

events = [
    json.loads(line)
    for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal([event["type"] for event in events], ["snapshot", "truncation"], "snapshot and truncation events")
assert_equal(events[0]["complete"], False, "snapshot event incomplete")
assert_equal(events[1]["snapshot_id"], "0001-codex", "truncation snapshot id")
assert_equal(events[1]["byte_ceiling"], 8, "truncation byte ceiling")
assert_equal(events[1]["omitted_bytes"], record["omitted_bytes"], "truncation omitted bytes")

try:
    broker.reconstruct_snapshot(
        session_dir=session_dir,
        snapshot_id="0001-codex",
        output_dir=fixture_root / "reconstructed",
    )
except ValueError as exc:
    assert "snapshot is incomplete" in str(exc)
else:
    raise AssertionError("incomplete snapshot should not reconstruct")
PY

echo "harness_deliberation_truncation_test: PASS"
