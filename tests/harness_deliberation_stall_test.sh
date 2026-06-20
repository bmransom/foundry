#!/usr/bin/env bash
# Unit checks for deterministic harness-deliberation stall detection.
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
import sys

broker_path = pathlib.Path(sys.argv[1])
fixture_root = pathlib.Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("harness_deliberation_broker", broker_path)
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def make_repo():
    repo = fixture_root / "stall"
    repo.mkdir()
    for path, body in {
        "AGENTS.md": "# Instructions\n",
        "knowledge/glossary.md": "---\ntitle: Glossary\n---\n# Glossary\n",
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
    return repo


repo = make_repo()
prompt = repo / "prompt.md"
prompt.write_text("Detect stalls.\n", encoding="utf-8")
started = broker.start_session(
    repo_root=repo,
    prompt_file=prompt,
    session_id="stall-demo",
    base_commit="abc1234",
    command_exists=lambda command: command in {"tmux", "git", "codex", "claude"},
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=lambda repo_root, harnesses: [
        {"harness": harness, "category": "ok"} for harness in harnesses
    ],
    run_tmux=False,
)


def runner(actor, prompt_path, raw_path):
    return broker.ParticipantResult(final=f"{actor} says no new decisions\n", raw="")


broker.run_round(session_dir=started.session_dir, participant_runner=runner)
events = [
    json.loads(line)
    for line in (started.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert "stall" not in [event["type"] for event in events], "first no-progress round should not stall"

broker.run_round(session_dir=started.session_dir, participant_runner=runner)
events = [
    json.loads(line)
    for line in (started.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
stall_events = [event for event in events if event["type"] == "stall"]
assert_equal(len(stall_events), 1, "one stall event")
stall = stall_events[0]
assert_equal(stall["round_id"], "r0002", "stall round")
assert_equal(stall["stall_rounds"], 2, "stall threshold")
assert_equal(len(stall["last_progress_hash"]), 64, "stall progress hash")
state = json.loads((started.session_dir / "state.json").read_text(encoding="utf-8"))
assert_equal(state["last_progress_hash"], stall["last_progress_hash"], "state progress hash matches stall")
PY

echo "harness_deliberation_stall_test: PASS"
