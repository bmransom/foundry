#!/usr/bin/env bash
# Unit checks for harness-deliberation preflight and start behavior.
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
import hashlib
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


def make_repo(name, harnesses=None):
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
    if harnesses is not None:
        (repo / ".foundry").mkdir()
        (repo / ".foundry/manifest.json").write_text(
            json.dumps(
                {
                    "pluginVersion": "1.0.0",
                    "conventionVersion": 3,
                    "harnesses": harnesses,
                    "files": {},
                }
            )
            + "\n",
            encoding="utf-8",
        )
    return repo


def command_exists(names):
    return lambda name: name in names


def ok_status(repo_root, harnesses):
    return [{"harness": harness, "category": "ok"} for harness in harnesses]


def assert_preflight_fails(repo, fragments, **kwargs):
    result = broker.run_start_preflight(repo_root=repo, **kwargs)
    assert not result.ok, "preflight should fail"
    message = "\n".join(failure["message"] for failure in result.failures)
    for fragment in fragments:
        assert fragment in message, f"expected {fragment!r} in {message!r}"


good_repo = make_repo("good", ["claude-code", "codex"])
prompt = good_repo / "prompt.md"
prompt.write_text("Design the broker.\n", encoding="utf-8")

ok_preflight = broker.run_start_preflight(
    repo_root=good_repo,
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
)
assert ok_preflight.ok, ok_preflight.failures

assert_preflight_fails(
    good_repo,
    ["missing required command", "tmux"],
    command_exists=command_exists({"git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
)

assert_preflight_fails(
    good_repo,
    ["git worktree", "failed"],
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(1, "", "no worktree"),
    harness_status_checker=ok_status,
)

missing_manifest_repo = make_repo("missing-manifest", None)
assert_preflight_fails(
    missing_manifest_repo,
    [".foundry/manifest.json", "missing"],
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
)

missing_harness_repo = make_repo("missing-harness", ["claude-code"])
assert_preflight_fails(
    missing_harness_repo,
    ["missing harnesses", "codex", "present: claude-code"],
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
)

unavailable_repo = make_repo("unavailable", ["claude-code", "codex"])
assert_preflight_fails(
    unavailable_repo,
    ["claude-code", "subscription-unavailable"],
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=lambda repo_root, harnesses: [
        {"harness": "codex", "category": "ok"},
        {"harness": "claude-code", "category": "subscription-unavailable", "detail": "plan disabled"},
    ],
)

result = broker.start_session(
    repo_root=good_repo,
    prompt_file=prompt,
    session_id="demo-start",
    attach=True,
    is_interactive=False,
    base_commit="abc1234",
    command_exists=command_exists({"tmux", "git", "codex", "claude"}),
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
    run_tmux=False,
)

session_dir = good_repo / ".foundry/tmp/harness-deliberation/demo-start"
assert_equal(result.session_dir, session_dir, "session dir")
assert_equal(result.tmux_session, "foundry-hd-demo-start", "tmux session name")
assert_equal(result.attach_command, "tmux attach -t foundry-hd-demo-start", "attach command")
assert any(command[:4] == ["tmux", "new-session", "-d", "-s"] and "control" in command for command in result.tmux_commands), "control window command"
assert any(command[:3] == ["tmux", "new-window", "-t"] and "state" in command for command in result.tmux_commands), "state window command"
# Panes follow each participant's latest final.md (long-lived, not placeholders).
joined = [" ".join(command) for command in result.tmux_commands]
assert not any("codex pane" in command for command in joined), "placeholder codex pane survives"
assert any("-codex" in command and "final.md" in command for command in joined), "codex final pane command"
assert any("-claude" in command and "final.md" in command for command in joined), "claude final pane command"
assert any("FOUNDRY_HD_SESSION" in command for command in joined), "mediator pane exports FOUNDRY_HD_SESSION"

# render_views ran during start, so the state window has Tier 3 views to tail.
assert (session_dir / "state.md").exists(), "state.md missing after start"
assert (session_dir / "transcript.md").exists(), "transcript.md missing after start"

events = [
    json.loads(line)
    for line in (session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert_equal([event["type"] for event in events], ["session_started", "mediator_prompt"], "start event types")
assert_equal(events[0]["repo_root"], str(good_repo), "session started repo root")
assert_equal(events[0]["base_commit"], "abc1234", "session started base commit")
assert_equal(events[0]["participants"], ["codex", "claude-code"], "session participants")
payload = events[1]["payloads"]["prompt"]
assert_equal(payload["path"], "mediator/prompt.md", "mediator prompt path")
assert_equal(payload["sha256"], hashlib.sha256(b"Design the broker.\n").hexdigest(), "mediator prompt hash")
assert_equal((session_dir / "mediator/prompt.md").read_text(encoding="utf-8"), "Design the broker.\n", "prompt copied")
PY

echo "harness_deliberation_start_test: PASS"
