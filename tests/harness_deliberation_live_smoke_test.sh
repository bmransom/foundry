#!/usr/bin/env bash
# Unit checks for opt-in harness-deliberation live smoke plumbing.
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

assert broker.DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD == "0.25"


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


def make_repo(name):
    repo = fixture_root / name
    repo.mkdir()
    run(["git", "init", "-b", "main"], cwd=repo)
    run(["git", "config", "user.email", "foundry@example.test"], cwd=repo)
    run(["git", "config", "user.name", "Foundry Test"], cwd=repo)
    for path, body in {
        ".gitignore": ".foundry/tmp/\n",
        "AGENTS.md": "# Instructions\n",
        "knowledge/glossary.md": "---\ntitle: Glossary\n---\n# Glossary\n",
        "knowledge/validation.md": "---\ntitle: Validation\n---\n# Validation\n",
        "roadmap/specs/README.md": "---\ntitle: Specs\n---\n# Specs\n",
        "roadmap/ROADMAP.md": "# Roadmap\n",
    }.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    (repo / ".foundry").mkdir()
    (repo / ".foundry/manifest.json").write_text(
        json.dumps(
            {
                "pluginVersion": "1.0.0",
                "conventionVersion": 3,
                "harnesses": ["claude-code", "codex"],
                "files": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run(["git", "add", "."], cwd=repo)
    run(["git", "commit", "-m", "fixture"], cwd=repo)
    return repo


def ok_status(repo_root, harnesses):
    return [{"harness": harness, "category": "ok"} for harness in harnesses]


repo = make_repo("live-smoke")
calls = []


def fake_live_runner(actor, prompt_path, raw_path):
    calls.append((actor, prompt_path.name, raw_path.name))
    prompt = prompt_path.read_text(encoding="utf-8")
    assert "# Harness Deliberation Turn" in prompt
    return broker.ParticipantResult(
        final=f"{actor} live smoke final\n",
        raw=f"{actor} raw event stream\n",
    )


result = broker.run_live_smoke(
    repo_root=repo,
    session_id="smoke-demo",
    prompt_text="Run the opt-in live smoke.\n",
    participant_runner=fake_live_runner,
    harness_status_checker=ok_status,
    run_tmux=False,
)

assert_equal(result["worktree_unchanged"], True, "worktree unchanged")
assert_equal(result["participants"], ["codex", "claude-code"], "participant order")
assert_equal(calls[0][0], "codex", "first live participant")
assert_equal(calls[1][0], "claude-code", "second live participant")
session_dir = pathlib.Path(result["session_dir"])
assert_equal(
    (session_dir / "turns/0001-codex/final.md").read_text(encoding="utf-8"),
    "codex live smoke final\n",
    "codex final payload",
)
assert_equal(
    (session_dir / "turns/0002-claude/final.md").read_text(encoding="utf-8"),
    "claude-code live smoke final\n",
    "claude final payload",
)
events = [
    json.loads(line)
    for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal(
    [event["type"] for event in events[-2:]],
    ["participant_final", "participant_final"],
    "participant final events",
)

mutating_repo = make_repo("mutating-live-smoke")


def mutating_runner(actor, prompt_path, raw_path):
    (mutating_repo / "mutation.txt").write_text("unexpected\n", encoding="utf-8")
    return broker.ParticipantResult(final=f"{actor}\n", raw="")


try:
    broker.run_live_smoke(
        repo_root=mutating_repo,
        session_id="mutating-smoke",
        prompt_text="Run the opt-in live smoke.\n",
        participant_runner=mutating_runner,
        harness_status_checker=ok_status,
        run_tmux=False,
    )
except RuntimeError as exc:
    assert "consumer repo worktree changed" in str(exc)
else:
    raise AssertionError("mutating live smoke should fail")
PY

if python3 "$BROKER" live-smoke --help 2>&1 | grep -q -- "--session"; then
  :
else
  fail "live-smoke CLI must expose --session"
fi

echo "harness_deliberation_live_smoke_test: PASS"
