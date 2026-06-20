#!/usr/bin/env bash
# Unit checks for harness-deliberation session storage primitives.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$BROKER" ] || fail "missing broker script"

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT

python3 - "$BROKER" "$fixture" <<'PY'
import hashlib
import importlib.util
import json
import pathlib
import sys

broker_path = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2])
session_dir = fixture / ".foundry" / "tmp" / "harness-deliberation" / "demo-session"

spec = importlib.util.spec_from_file_location("harness_deliberation_broker", broker_path)
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def read_events():
    with (session_dir / "events.jsonl").open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def create_store(name):
    return broker.SessionStore.create(
        session_dir=fixture / name,
        session_id=name,
        repo_root=fixture,
        base_commit="abc1234",
        participants=["codex", "claude-code"],
        config={"stall_rounds": 2},
    )


def create_payload_store(name):
    payload_store = create_store(name)
    prompt = payload_store.write_payload("turns/0001-codex/prompt.md", "Prompt body\n")
    final = payload_store.write_payload("turns/0001-codex/final.md", "Final body\n")
    payload_store.append_event(
        "participant_final",
        {
            "actor": "codex",
            "round_id": "r0001",
            "turn_id": "0001-codex",
            "payloads": {"prompt": prompt, "final": final},
        },
    )
    return payload_store


def assert_rebuild_fails(failing_store, fragments):
    try:
        failing_store.rebuild()
    except ValueError as exc:
        message = str(exc)
        for fragment in fragments:
            assert fragment in message, f"expected {fragment!r} in {message!r}"
    else:
        raise AssertionError(f"rebuild should fail with {fragments!r}")


store = broker.SessionStore.create(
    session_dir=session_dir,
    session_id="demo-session",
    repo_root=fixture,
    base_commit="abc1234",
    participants=["codex", "claude-code"],
    config={"stall_rounds": 2},
)

session = json.loads((session_dir / "session.json").read_text(encoding="utf-8"))
assert_equal(session["session_id"], "demo-session", "session id")
assert_equal(session["repo_root"], str(fixture), "repo root")
assert_equal(session["base_commit"], "abc1234", "base commit")
assert_equal(session["participants"], ["codex", "claude-code"], "participants")
assert_equal(session["config"]["stall_rounds"], 2, "stall rounds")
assert_equal((session_dir / "events.jsonl").read_text(encoding="utf-8"), "", "new ledger")

prompt_payload = store.write_payload("turns/0001-codex/prompt.md", "Prompt body\n")
expected_prompt_hash = hashlib.sha256(b"Prompt body\n").hexdigest()
assert_equal(prompt_payload["path"], "turns/0001-codex/prompt.md", "payload path")
assert_equal(prompt_payload["sha256"], expected_prompt_hash, "payload hash")
assert_equal(prompt_payload["bytes"], len(b"Prompt body\n"), "payload byte count")

try:
    store.write_payload("turns/0001-codex/prompt.md", "different body\n")
except ValueError as exc:
    assert "immutable payload exists" in str(exc)
else:
    raise AssertionError("payload overwrite should fail")

final_payload = store.write_payload("turns/0001-codex/final.md", "Final body\n")

event = store.append_event(
    "repo_guidance",
    {
        "actor": "broker",
        "guidance": [
            {
                "path": "AGENTS.md",
                "role": "standing-rules",
                "required": True,
                "exists": True,
                "sha256": expected_prompt_hash,
            }
        ],
    },
)
assert_equal(event["event_id"], "e000001", "first event id")
assert_equal(event["type"], "repo_guidance", "first event type")

turn_event = store.append_event(
    "participant_final",
    {
        "actor": "codex",
        "round_id": "r0001",
        "turn_id": "0001-codex",
        "payloads": {"prompt": prompt_payload, "final": final_payload},
        "raw_path": "turns/0001-codex/raw.log",
    },
)
assert_equal(turn_event["event_id"], "e000002", "second event id")
assert_equal(turn_event["turn_id"], "0001-codex", "turn id preserved")
assert_equal(turn_event["payloads"]["prompt"]["sha256"], expected_prompt_hash, "prompt hash in event")

reopened = broker.SessionStore.open(session_dir)
question = reopened.append_event(
    "question",
    {
        "actor": "mediator",
        "question_id": "q0001",
        "text": "Which session protocol is v1?",
    },
)
decision = reopened.append_event(
    "decision",
    {
        "actor": "mediator",
        "decision_id": "d0001",
        "question_id": "q0001",
        "disposition": "settled",
        "summary": "Use an append-only event ledger.",
    },
)
revision = reopened.append_event(
    "decision",
    {
        "actor": "mediator",
        "decision_id": "d0002",
        "question_id": "q0001",
        "disposition": "deferred-dissent",
        "summary": "Keep the ledger, but record the dissenting tradeoff.",
        "supersedes": decision["event_id"],
    },
)
assert_equal(question["event_id"], "e000003", "event id after reopen")
assert_equal(revision["supersedes"], "e000004", "decision revision link")

before_unknown = (session_dir / "events.jsonl").read_bytes()
try:
    reopened.append_event("guidance_manifest", {"actor": "broker"})
except ValueError as exc:
    assert "unknown event type" in str(exc)
else:
    raise AssertionError("unknown event type should fail")
assert_equal((session_dir / "events.jsonl").read_bytes(), before_unknown, "unknown event does not append")

for event_type in [
    "session_started",
    "mediator_prompt",
    "participant_failed",
    "participant_limited",
    "snapshot",
    "truncation",
    "stall",
]:
    reopened.append_event(event_type, {"actor": "broker"})

events = read_events()
assert_equal([event["event_id"] for event in events], [f"e{i:06d}" for i in range(1, 13)], "monotonic ids")
assert_equal(events[3]["event_id"], "e000004", "original decision retained")
assert_equal(events[4]["event_id"], "e000005", "revision appended")
assert_equal(events[4]["supersedes"], "e000004", "revision relationship in ledger")
assert_equal(events[1]["payloads"]["final"]["path"], "turns/0001-codex/final.md", "immutable final path recorded")

expected_types = {
    "session_started",
    "mediator_prompt",
    "repo_guidance",
    "participant_final",
    "participant_failed",
    "participant_limited",
    "question",
    "decision",
    "snapshot",
    "truncation",
    "stall",
}
assert_equal(broker.KNOWN_EVENT_TYPES, expected_types, "closed event type set")

reopened.render_views()
first_views = {
    name: (session_dir / name).read_bytes()
    for name in ["state.json", "state.md", "transcript.md"]
}

state = json.loads((session_dir / "state.json").read_text(encoding="utf-8"))
assert_equal(state["session_id"], "demo-session", "state session id")
assert_equal(state["event_count"], 12, "state event count")
assert_equal(state["questions"]["q0001"]["text"], "Which session protocol is v1?", "state question text")
assert_equal(state["open_questions"], [], "decision closes question")
assert "d0001" not in state["decisions"], "superseded decision is not effective"
assert_equal(state["decisions"]["d0002"]["disposition"], "deferred-dissent", "effective revised disposition")
assert_equal(state["decisions"]["d0002"]["supersedes"], "e000004", "state preserves revision link")
assert_equal(state["deferred_dissent"], ["d0002"], "deferred dissent list")
assert_equal(state["rounds"], {"r0001": ["0001-codex"]}, "round grouping")
assert_equal(len(state["last_progress_hash"]), 64, "progress hash length")

state_md = (session_dir / "state.md").read_text(encoding="utf-8")
assert "# State - demo-session" in state_md
assert "- Open questions: none" in state_md
assert "- Deferred dissent: d0002" in state_md
assert "- r0001: 0001-codex" in state_md

transcript = (session_dir / "transcript.md").read_text(encoding="utf-8")
assert "# Transcript - demo-session" in transcript
assert "- e000002 `participant_final` actor=codex round=r0001 turn=0001-codex" in transcript
assert "  - final: turns/0001-codex/final.md" in transcript
assert "- e000005 `decision` actor=mediator" in transcript

for name in first_views:
    (session_dir / name).unlink()
reopened.render_views()
second_views = {
    name: (session_dir / name).read_bytes()
    for name in ["state.json", "state.md", "transcript.md"]
}
assert_equal(second_views, first_views, "tier 3 views rebuild byte-identically")

reopened.rebuild()
third_views = {
    name: (session_dir / name).read_bytes()
    for name in ["state.json", "state.md", "transcript.md"]
}
assert_equal(third_views, first_views, "rebuild keeps deterministic views")

corrupt_store = create_payload_store("corrupt-payload")
(corrupt_store.session_dir / "turns/0001-codex/final.md").write_text("Corrupted body\n", encoding="utf-8")
assert_rebuild_fails(corrupt_store, ["payload hash mismatch", "turns/0001-codex/final.md"])

missing_store = create_payload_store("missing-payload")
(missing_store.session_dir / "turns/0001-codex/final.md").unlink()
assert_rebuild_fails(missing_store, ["missing payload", "turns/0001-codex/final.md"])

invalid_store = create_store("invalid-disposition")
invalid_store.append_event(
    "question",
    {
        "actor": "mediator",
        "question_id": "q0001",
        "text": "Which disposition is valid?",
    },
)
invalid_store.append_event(
    "decision",
    {
        "actor": "mediator",
        "decision_id": "d0001",
        "question_id": "q0001",
        "disposition": "unsupported",
        "summary": "This should not replay.",
    },
)
assert_rebuild_fails(invalid_store, ["invalid disposition", "d0001", "unsupported"])

nondeterministic_store = create_payload_store("nondeterministic-view")
nondeterministic_store.rebuild()
(nondeterministic_store.session_dir / "state.md").write_text("tampered\n", encoding="utf-8")
assert_rebuild_fails(nondeterministic_store, ["tier 3 view differs", "state.md"])
PY

echo "harness_deliberation_broker_test: PASS"
