#!/usr/bin/env bash
# T35: the live start/tmux path must build long-lived panes and Tier 3 views.
# This drives real tmux (not run_tmux=False): it fails if the control panes exit
# on their own (placeholder panes) or if state.md/transcript.md are missing.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$BROKER" ] || fail "missing broker script"

if ! command -v tmux >/dev/null 2>&1; then
  echo "harness_deliberation_start_tmux_test: SKIP (no tmux)"
  exit 0
fi

fixture_root="$(mktemp -d)"
session_id="tmuxtest-$$"
tmux_session="foundry-hd-${session_id}"
cleanup() {
  tmux kill-session -t "$tmux_session" 2>/dev/null || true
  rm -rf "$fixture_root"
}
trap cleanup EXIT

# A stale session of this name would poison new-session; clear it first.
tmux kill-session -t "$tmux_session" 2>/dev/null || true

python3 - "$BROKER" "$fixture_root" "$session_id" "$tmux_session" <<'PY'
import importlib.util
import json
import pathlib
import subprocess
import sys
import time

broker_path = pathlib.Path(sys.argv[1])
fixture_root = pathlib.Path(sys.argv[2])
session_id = sys.argv[3]
tmux_session = sys.argv[4]

spec = importlib.util.spec_from_file_location("harness_deliberation_broker", broker_path)
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)

repo = fixture_root / "repo"
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
prompt = repo / "prompt.md"
prompt.write_text("Shape the spec.\n", encoding="utf-8")


def ok_status(repo_root, harnesses):
    return [{"harness": harness, "category": "ok"} for harness in harnesses]


# run_tmux=True drives real tmux; preflight command existence + harness status
# are faked so the test does not require codex/claude binaries.
result = broker.start_session(
    repo_root=repo,
    prompt_file=prompt,
    session_id=session_id,
    base_commit="abc1234",
    command_exists=lambda name: True,
    harness_status_checker=ok_status,
    run_tmux=True,
)
assert result.tmux_session == tmux_session, (result.tmux_session, tmux_session)

session_dir = result.session_dir
# render_views must have run so the state window has something to tail.
assert (session_dir / "state.md").exists(), "state.md missing after start (render_views not called)"
assert (session_dir / "transcript.md").exists(), "transcript.md missing after start"

# Placeholder panes exit immediately and tear down the control window. Give the
# session a moment to settle, then the control window must still hold three panes.
time.sleep(1.0)
listed = subprocess.run(
    ["tmux", "list-panes", "-t", f"{tmux_session}:control", "-F", "#{pane_id}"],
    capture_output=True,
    text=True,
)
assert listed.returncode == 0, f"control window gone (panes exited): {listed.stderr!r}"
panes = [line for line in listed.stdout.splitlines() if line.strip()]
assert len(panes) == 3, f"expected 3 long-lived control panes, got {len(panes)}: {listed.stdout!r}"

print("driver ok")
PY

echo "harness_deliberation_start_tmux_test: PASS"
