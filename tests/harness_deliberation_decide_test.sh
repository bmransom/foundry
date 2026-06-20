#!/usr/bin/env bash
# Unit checks for harness-deliberation mediator question and decision flow.
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


def make_repo(name):
    repo = fixture_root / name
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


def start_session(repo, name):
    prompt = repo / "prompt.md"
    prompt.write_text("Decide mediator questions.\n", encoding="utf-8")
    return broker.start_session(
        repo_root=repo,
        prompt_file=prompt,
        session_id=name,
        base_commit="abc1234",
        command_exists=lambda command: command in {"tmux", "git", "codex", "claude"},
        command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
        harness_status_checker=lambda repo_root, harnesses: [
            {"harness": harness, "category": "ok"} for harness in harnesses
        ],
        run_tmux=False,
    )


repo = make_repo("decide")
started = start_session(repo, "decide-demo")

broker.apply_decisions(
    session_dir=started.session_dir,
    questions=[
        {"question_id": "q0001", "text": "Which UI is v1?"},
        {"question_id": "q0002", "text": "Should raw logs affect rebuild?"},
    ],
)
state = json.loads((started.session_dir / "state.json").read_text(encoding="utf-8"))
assert_equal(state["open_questions"], ["q0001", "q0002"], "questions start open")

broker.apply_decisions(
    session_dir=started.session_dir,
    decisions=[
        {
            "decision_id": "d0001",
            "question_id": "q0001",
            "disposition": "settled",
            "summary": "Use tmux/TUI for v1.",
        },
        {
            "decision_id": "d0002",
            "question_id": "q0002",
            "disposition": "rejected",
            "summary": "Do not use raw logs for rebuild.",
        },
    ],
)
state = json.loads((started.session_dir / "state.json").read_text(encoding="utf-8"))
assert_equal(state["open_questions"], [], "decisions close questions")
assert_equal(state["decisions"]["d0001"]["disposition"], "settled", "settled decision")
assert_equal(state["decisions"]["d0002"]["disposition"], "rejected", "rejected decision")

events = [
    json.loads(line)
    for line in (started.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
original_decision_event = next(event["event_id"] for event in events if event.get("decision_id") == "d0001")

file_payload = {
    "questions": [{"question_id": "q0003", "text": "Which dissent remains?"}],
    "decisions": [
        {
            "decision_id": "d0003",
            "question_id": "q0003",
            "disposition": "deferred-dissent",
            "summary": "Keep dissent as a named tradeoff.",
        },
        {
            "decision_id": "d0004",
            "question_id": "q0001",
            "disposition": "deferred-dissent",
            "summary": "Revise the UI decision into a tradeoff.",
            "supersedes": original_decision_event,
        },
    ],
}
decision_file = repo / "decisions.json"
decision_file.write_text(json.dumps(file_payload), encoding="utf-8")
assert_equal(
    broker.main(["decide", "--session-dir", str(started.session_dir), "--file", str(decision_file)]),
    0,
    "decide CLI exit",
)
state = json.loads((started.session_dir / "state.json").read_text(encoding="utf-8"))
assert "d0001" not in state["decisions"], "superseded decision hidden from effective state"
assert_equal(state["decisions"]["d0004"]["supersedes"], original_decision_event, "revision link")
assert_equal(state["deferred_dissent"], ["d0003", "d0004"], "deferred dissent state")

try:
    broker.apply_decisions(
        session_dir=started.session_dir,
        decisions=[
            {
                "decision_id": "d9999",
                "question_id": "q0001",
                "disposition": "maybe",
                "summary": "Invalid.",
            }
        ],
    )
except ValueError as exc:
    assert "invalid disposition" in str(exc)
    assert "maybe" in str(exc)
else:
    raise AssertionError("invalid disposition should fail")

try:
    broker.apply_decisions(
        session_dir=started.session_dir,
        decisions=[
            {
                "decision_id": "d9998",
                "question_id": "missing-question",
                "disposition": "settled",
                "summary": "Invalid.",
            }
        ],
    )
except ValueError as exc:
    assert "unknown question_id" in str(exc)
else:
    raise AssertionError("unknown question should fail")
PY

echo "harness_deliberation_decide_test: PASS"
