#!/usr/bin/env bash
# Unit checks for round resumability, participant_failed, and the round CLI.
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
    return repo


def command_exists(name):
    return name in {"tmux", "git", "codex", "claude"}


def ok_status(repo_root, harnesses):
    return [{"harness": harness, "category": "ok"} for harness in harnesses]


def start(repo, session_id):
    prompt = repo / "prompt.md"
    prompt.write_text("Shape the spec.\n", encoding="utf-8")
    return broker.start_session(
        repo_root=repo,
        prompt_file=prompt,
        session_id=session_id,
        base_commit="abc1234",
        command_exists=command_exists,
        command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
        harness_status_checker=ok_status,
        run_tmux=False,
    )


def events_of(session_dir):
    return [
        json.loads(line)
        for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def good_runner(actor, prompt_path, raw_path):
    return broker.ParticipantResult(final=f"{actor} substantive answer\n", raw="r")


# 1. write_payload is idempotent on identical content, rejects a real conflict.
idem = start(make_repo("idem"), "idem")
store = broker.SessionStore.open(idem.session_dir)
first = store.write_payload("probe.md", "same bytes")
again = store.write_payload("probe.md", "same bytes")
assert_equal(again["sha256"], first["sha256"], "idempotent payload hash")
try:
    store.write_payload("probe.md", "different bytes")
except ValueError as exc:
    assert "immutable payload exists" in str(exc), "conflict message"
else:
    raise AssertionError("write_payload must reject a changed payload")


# 2. participant_failed: an unclassified nonzero exit is recorded, not raised.
failed_start = start(make_repo("failed"), "failed")


def failing_runner(actor, prompt_path, raw_path):
    raise broker.ParticipantFailed(actor=actor, exit_code=3, detail="boom from cli")


broker.run_round(session_dir=failed_start.session_dir, participant_runner=failing_runner)
failed_events = events_of(failed_start.session_dir)
assert_equal(failed_events[-1]["type"], "participant_failed", "failed event type")
assert_equal(failed_events[-1]["actor"], "codex", "failed actor")
assert_equal(failed_events[-1]["exit_code"], 3, "failed exit code")
assert_equal(failed_events[-1]["payloads"]["prompt"]["path"], "turns/0001-codex/prompt.md", "failed prompt payload")
assert "participant_final" not in [e["type"] for e in failed_events], "round stops after failure"


# 3. partial-round resume: a limited first participant does not burn the round.
resume_start = start(make_repo("resume"), "resume")


def limited_runner(actor, prompt_path, raw_path):
    raise broker.ParticipantLimited(actor=actor, category="rate-limited", detail="slow down")


broker.run_round(session_dir=resume_start.session_dir, participant_runner=limited_runner)
broker.run_round(session_dir=resume_start.session_dir, participant_runner=good_runner)
resume_events = events_of(resume_start.session_dir)
finals = [e for e in resume_events if e["type"] == "participant_final"]
assert_equal(sorted(e["actor"] for e in finals), ["claude-code", "codex"], "both participants finished")
round_ids = {e.get("round_id") for e in resume_events if e.get("round_id")}
assert_equal(round_ids, {"r0001"}, "resumed the same round, did not advance to r0002")
guidance_rounds = [e["round_id"] for e in resume_events if e["type"] == "repo_guidance"]
assert_equal(guidance_rounds, ["r0001"], "repo_guidance not re-appended on resume")


# 4. round CLI dispatches over an existing session with a fake runner.
cli_start = start(make_repo("cli"), "cli")


def fake_round_factory(repo, timeout_s, budget_usd):
    return good_runner


broker._round_participant_runner = fake_round_factory
code = broker.main(["round", "--session-dir", str(cli_start.session_dir)])
assert_equal(code, 0, "round CLI exit code")
cli_finals = [e for e in events_of(cli_start.session_dir) if e["type"] == "participant_final"]
assert_equal(len(cli_finals), 2, "round CLI recorded a final per participant")

# 5. round CLI refuses a missing session and a session_id/dir mismatch.
assert_equal(broker.main(["round", "--session-dir", str(fixture_root / "nope")]), 1, "missing session exits nonzero")
mismatch_dir = fixture_root / "mismatch-dir"
broker.SessionStore.create(
    session_dir=mismatch_dir,
    session_id="other-id",
    repo_root=make_repo("mismatch"),
    base_commit="abc1234",
    participants=broker.REQUIRED_HARNESSES,
)
assert_equal(broker.main(["round", "--session-dir", str(mismatch_dir)]), 1, "session_id mismatch exits nonzero")
PY

echo "harness_deliberation_resume_test: PASS"
