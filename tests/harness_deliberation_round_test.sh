#!/usr/bin/env bash
# Unit checks for harness-deliberation fake participant rounds.
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


repo = make_repo("round")
prompt = repo / "prompt.md"
prompt.write_text("Shape the spec.\n", encoding="utf-8")
started = broker.start_session(
    repo_root=repo,
    prompt_file=prompt,
    session_id="round-demo",
    base_commit="abc1234",
    command_exists=command_exists,
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
    run_tmux=False,
)

seen_prompts = {}


def participant_runner(actor, prompt_path, raw_path):
    prompt_body = prompt_path.read_text(encoding="utf-8")
    seen_prompts[actor] = prompt_body
    return broker.ParticipantResult(
        final=f"{actor} final\n",
        raw=f"{actor} raw secret\n",
    )


broker.run_round(session_dir=started.session_dir, participant_runner=participant_runner)

events = [
    json.loads(line)
    for line in (started.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal(
    [event["type"] for event in events],
    [
        "session_started",
        "mediator_prompt",
        "repo_guidance",
        "participant_final",
        "participant_final",
    ],
    "round event types",
)
guidance = events[2]["guidance"]
assert_equal([item["path"] for item in guidance][:4], broker.REQUIRED_GUIDANCE_PATHS, "required guidance order")
assert all(item["exists"] for item in guidance if item["required"]), "required guidance exists"
assert_equal(events[3]["actor"], "codex", "first actor")
assert_equal(events[4]["actor"], "claude-code", "second actor")
assert_equal(events[3]["round_id"], "r0001", "codex round")
assert_equal(events[4]["round_id"], "r0001", "claude round")
assert_equal(events[3]["turn_id"], "0001-codex", "codex turn")
assert_equal(events[4]["turn_id"], "0002-claude", "claude turn")
assert_equal(events[3]["payloads"]["prompt"]["path"], "turns/0001-codex/prompt.md", "codex prompt payload")
assert_equal(events[4]["payloads"]["final"]["path"], "turns/0002-claude/final.md", "claude final payload")
assert "raw" not in events[3]["payloads"], "raw output not a hashed payload"

codex_prompt = seen_prompts["codex"]
claude_prompt = seen_prompts["claude-code"]
assert "AGENTS.md" in codex_prompt
assert "knowledge/glossary.md" in codex_prompt
assert "# Compact State" in codex_prompt
assert "codex final" in claude_prompt
assert "codex raw secret" not in claude_prompt
assert_equal((started.session_dir / "turns/0001-codex/final.md").read_text(encoding="utf-8"), "codex final\n", "codex final file")

(started.session_dir / "turns/0001-codex/raw.log").write_text("corrupted debug raw\n", encoding="utf-8")
broker.SessionStore.open(started.session_dir).rebuild()

limited_repo = make_repo("limited")
limited_prompt = limited_repo / "prompt.md"
limited_prompt.write_text("Shape the spec.\n", encoding="utf-8")
limited_start = broker.start_session(
    repo_root=limited_repo,
    prompt_file=limited_prompt,
    session_id="limited-demo",
    base_commit="abc1234",
    command_exists=command_exists,
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
    run_tmux=False,
)


def limited_runner(actor, prompt_path, raw_path):
    raise broker.ParticipantLimited(
        actor=actor,
        category="usage-limited",
        detail="quota resets tomorrow",
        retry_at="2026-06-20T00:00:00Z",
    )


broker.run_round(session_dir=limited_start.session_dir, participant_runner=limited_runner)
limited_events = [
    json.loads(line)
    for line in (limited_start.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal(limited_events[-1]["type"], "participant_limited", "limited event type")
assert_equal(limited_events[-1]["actor"], "codex", "limited actor")
assert_equal(limited_events[-1]["category"], "usage-limited", "limited category")
assert_equal(limited_events[-1]["retry_at"], "2026-06-20T00:00:00Z", "retry metadata")
PY

echo "harness_deliberation_round_test: PASS"
