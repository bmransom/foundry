#!/usr/bin/env bash
# Unit checks for traceable harness-deliberation spec generation.
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


def create_session(name):
    session_dir = fixture_root / f".foundry/tmp/harness-deliberation/{name}"
    store = broker.SessionStore.create(
        session_dir=session_dir,
        session_id=name,
        repo_root=fixture_root,
        base_commit="abc1234",
        participants=["codex", "claude-code"],
        config={"stall_rounds": 2},
    )
    return store, session_dir


store, session_dir = create_session("spec-generation")
evidence = store.write_payload("evidence/final.md", "supporting evidence\n")
broker.apply_decisions(
    session_dir=session_dir,
    questions=[
        {"question_id": "q0001", "text": "Requirement?"},
        {"question_id": "q0002", "text": "Design?"},
        {"question_id": "q0003", "text": "Task?"},
        {"question_id": "q0004", "text": "Deferred dissent?"},
        {"question_id": "q0005", "text": "Rejected output?"},
    ],
    decisions=[
        {
            "decision_id": "d0001",
            "question_id": "q0001",
            "disposition": "settled",
            "summary": "The broker records sessions.",
            "outputs": {
                "requirements": [
                    "WHEN start runs, THE SYSTEM SHALL create session storage."
                ]
            },
            "payloads": {"supporting": evidence},
        },
        {
            "decision_id": "d0002",
            "question_id": "q0002",
            "disposition": "settled",
            "summary": "Use an append-only ledger.",
            "outputs": {"design": ["Use an append-only event ledger."]},
            "payloads": {"supporting": evidence},
        },
        {
            "decision_id": "d0003",
            "question_id": "q0003",
            "disposition": "settled",
            "summary": "Write broker tests first.",
            "outputs": {"tasks": ["Implement the broker with TDD."]},
            "payloads": {"supporting": evidence},
        },
        {
            "decision_id": "d0004",
            "question_id": "q0004",
            "disposition": "deferred-dissent",
            "summary": "A web UI may become useful after the TUI proves the protocol.",
            "payloads": {"supporting": evidence},
        },
        {
            "decision_id": "d0005",
            "question_id": "q0005",
            "disposition": "rejected",
            "summary": "Rejected web UI for v1.",
            "outputs": {"design": ["Build a web UI in v1."]},
            "payloads": {"supporting": evidence},
        },
    ],
)
out_dir = fixture_root / "generated-spec"
broker.generate_spec(session_dir=session_dir, out_dir=out_dir)
events = [
    json.loads(line)
    for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
event_by_decision = {
    event["decision_id"]: event["event_id"]
    for event in events
    if event.get("type") == "decision"
}
requirements = (out_dir / "requirements.md").read_text(encoding="utf-8")
design = (out_dir / "design.md").read_text(encoding="utf-8")
tasks = (out_dir / "tasks.md").read_text(encoding="utf-8")
assert "WHEN start runs, THE SYSTEM SHALL create session storage." in requirements
assert f"Trace: decision {event_by_decision['d0001']}; payload {evidence['sha256']}" in requirements
assert "Use an append-only event ledger." in design
assert f"Trace: decision {event_by_decision['d0002']}; payload {evidence['sha256']}" in design
assert "## Deferred Dissent" in design
assert "A web UI may become useful after the TUI proves the protocol." in design
assert f"Trace: decision {event_by_decision['d0004']}; payload {evidence['sha256']}" in design
assert "Build a web UI in v1." not in design
assert "Implement the broker with TDD." in tasks
assert f"Trace: decision {event_by_decision['d0003']}; payload {evidence['sha256']}" in tasks

unsupported_store, unsupported_dir = create_session("unsupported")
unsupported_payload = unsupported_store.write_payload("evidence/final.md", "evidence\n")
broker.apply_decisions(
    session_dir=unsupported_dir,
    questions=[{"question_id": "q0001", "text": "Unsupported?"}],
    decisions=[
        {
            "decision_id": "d9999",
            "question_id": "q0001",
            "disposition": "settled",
            "summary": "No output schema.",
            "payloads": {"supporting": unsupported_payload},
        }
    ],
)
try:
    broker.generate_spec(session_dir=unsupported_dir, out_dir=fixture_root / "unsupported-out")
except ValueError as exc:
    assert "unsupported decision" in str(exc)
    assert "d9999" in str(exc)
else:
    raise AssertionError("unsupported settled decision should fail")

missing_trace_store, missing_trace_dir = create_session("missing-trace")
broker.apply_decisions(
    session_dir=missing_trace_dir,
    questions=[{"question_id": "q0001", "text": "Trace?"}],
    decisions=[
        {
            "decision_id": "d9998",
            "question_id": "q0001",
            "disposition": "settled",
            "summary": "Has output but no supporting payload.",
            "outputs": {"design": ["Missing traceability."]},
        }
    ],
)
try:
    broker.generate_spec(session_dir=missing_trace_dir, out_dir=fixture_root / "missing-trace-out")
except ValueError as exc:
    assert "missing traceability" in str(exc)
    assert "d9998" in str(exc)
else:
    raise AssertionError("missing traceability should fail")

assert_equal(
    broker.main(["spec", "--session-dir", str(session_dir), "--out", str(fixture_root / "cli-spec")]),
    0,
    "spec CLI generation exit",
)
assert (fixture_root / "cli-spec/requirements.md").is_file(), "CLI writes requirements"
PY

echo "harness_deliberation_spec_generation_test: PASS"
