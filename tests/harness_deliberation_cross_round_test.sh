#!/usr/bin/env bash
# T34: a new round must carry each peer's latest final.md, not restart cold.
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


repo = make_repo("cross-round")
prompt = repo / "prompt.md"
prompt.write_text("Shape the spec.\n", encoding="utf-8")
started = broker.start_session(
    repo_root=repo,
    prompt_file=prompt,
    session_id="cross-round",
    base_commit="abc1234",
    command_exists=command_exists,
    command_runner=lambda command, timeout_s: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status,
    run_tmux=False,
)


def runner(actor, prompt_path, raw_path):
    return broker.ParticipantResult(final=f"{actor} round-final\n", raw="r")


# Round 1, then round 2.
broker.run_round(session_dir=started.session_dir, participant_runner=runner)
broker.run_round(session_dir=started.session_dir, participant_runner=runner)

events = [
    json.loads(line)
    for line in (started.session_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
# The first participant_final of round r0002 names the first turn of round 2.
r2_finals = [e for e in events if e["type"] == "participant_final" and e["round_id"] == "r0002"]
assert r2_finals, f"expected a round 2; rounds: {sorted({e.get('round_id') for e in events})}"
first_actor = r2_finals[0]["actor"]
first_turn = r2_finals[0]["turn_id"]
prompt_text = (started.session_dir / "turns" / first_turn / "prompt.md").read_text(encoding="utf-8")

# Round 2's first participant (claude-code) must see codex's round-1 final, not start cold.
assert "codex round-final" in prompt_text, (
    f"round 2 first participant ({first_actor}) lost the prior peer final:\n{prompt_text}"
)
assert "# Peer Finals\n- none" not in prompt_text, "round 2 started with empty peer finals"
PY

echo "harness_deliberation_cross_round_test: PASS"
