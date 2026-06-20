#!/usr/bin/env bash
# T36 / AC-8.6: `round` must re-check harness availability and refuse drift before
# spending a turn — a participant removed from the manifest (or unavailable) makes
# round exit nonzero with no participant turn, not fail mid-turn.
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

spec = importlib.util.spec_from_file_location("b", sys.argv[1])
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)
fixture_root = pathlib.Path(sys.argv[2])


def assert_equal(a, e, m):
    if a != e:
        raise AssertionError(f"{m}: expected {e!r}, got {a!r}")


def make_repo(name, harnesses):
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
        json.dumps({"pluginVersion": "1.0.0", "conventionVersion": 3, "harnesses": harnesses, "files": {}}) + "\n",
        encoding="utf-8",
    )
    return repo


def ok_status(repo_root, harnesses):
    return [{"harness": h, "category": "ok"} for h in harnesses]


# Start a healthy session (both harnesses), then drift the manifest to drop codex.
repo = make_repo("drift", ["claude-code", "codex"])
prompt = repo / "prompt.md"
prompt.write_text("Shape it.\n", encoding="utf-8")
started = broker.start_session(
    repo_root=repo, prompt_file=prompt, session_id="drift", base_commit="abc1234",
    command_exists=lambda n: True,
    command_runner=lambda c, t: broker.CommandResult(0, "ok", ""),
    harness_status_checker=ok_status, run_tmux=False,
)
# Drift: codex removed from the manifest after the session started.
(repo / ".foundry/manifest.json").write_text(
    json.dumps({"pluginVersion": "1.0.0", "conventionVersion": 3, "harnesses": ["claude-code"], "files": {}}) + "\n",
    encoding="utf-8",
)

# Make every NON-drift preflight check pass so the only failure is the drift.
broker._command_exists = lambda n: True
broker._run_command = lambda c, t: broker.CommandResult(0, "ok", "")
broker._check_harness_statuses = ok_status
# Even if preflight were skipped, the runner would record a final — so asserting
# "no final + exit 1" proves the drift refusal, not a runner failure.
broker._round_participant_runner = lambda repo_, t, b: (
    lambda actor, pp, rp: broker.ParticipantResult(final=f"{actor} final\n", raw="r")
)

code = broker.main(["round", "--session-dir", str(started.session_dir)])
events = [json.loads(l) for l in (started.session_dir / "events.jsonl").read_text().splitlines() if l.strip()]
finals = [e for e in events if e["type"] == "participant_final"]
assert_equal(code, 1, "round must exit nonzero on manifest drift")
assert_equal(len(finals), 0, "round must refuse before spending a turn (no participant_final)")
PY

echo "harness_deliberation_round_drift_test: PASS"
