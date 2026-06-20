#!/usr/bin/env bash
# Unit checks for harness-deliberation scratch worktree creation.
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
(repo / "README.md").write_text("# fixture\n", encoding="utf-8")
run(["git", "add", ".gitignore", "README.md"], cwd=repo)
run(["git", "commit", "-m", "initial"], cwd=repo)
base_commit = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo)

session_dir = repo / ".foundry/tmp/harness-deliberation/worktree-demo"
broker.SessionStore.create(
    session_dir=session_dir,
    session_id="worktree-demo",
    repo_root=repo,
    base_commit=base_commit,
    participants=["codex", "claude-code"],
    config={"stall_rounds": 2},
)

before_branch = run(["git", "branch", "--show-current"], cwd=repo)
before_status = run(["git", "status", "--short"], cwd=repo)

result = broker.create_scratch_worktrees(session_dir=session_dir)
assert_equal([item["actor"] for item in result], ["codex", "claude-code"], "scratch actor order")
assert result[0]["path"] != result[1]["path"], "scratch paths are separate"
assert result[0]["branch"] != result[1]["branch"], "scratch branches are separate"

expected = {
    "codex": f"foundry/hd/worktree-demo/codex",
    "claude-code": f"foundry/hd/worktree-demo/claude",
}
for item in result:
    path = pathlib.Path(item["path"])
    assert path.is_dir(), f"missing worktree path {path}"
    assert_equal(
        run(["git", "branch", "--show-current"], cwd=path),
        expected[item["actor"]],
        f"{item['actor']} branch",
    )
    assert_equal(
        run(["git", "rev-parse", "--short", "HEAD"], cwd=path),
        base_commit,
        f"{item['actor']} base commit",
    )

assert_equal(run(["git", "branch", "--show-current"], cwd=repo), before_branch, "consumer branch unchanged")
assert_equal(run(["git", "status", "--short"], cwd=repo), before_status, "consumer status unchanged")

try:
    broker.create_scratch_worktrees(session_dir=session_dir)
except ValueError as exc:
    assert "scratch worktree exists" in str(exc)
else:
    raise AssertionError("duplicate scratch worktree creation should fail")
PY

echo "harness_deliberation_worktree_test: PASS"
