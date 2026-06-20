#!/usr/bin/env bash
# Issue #6: a participant-turn timeout must not crash the round with
# "bytes is not JSON serializable". subprocess.TimeoutExpired.stdout/.stderr are
# bytes even under text=True; the timeout handlers must decode so CommandResult
# always holds str and _format_raw_turn can serialize it.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$BROKER" ] || fail "missing broker script"

python3 - "$BROKER" <<'PY'
import importlib.util
import json
import pathlib
import sys

spec = importlib.util.spec_from_file_location("b", sys.argv[1])
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)

# A command that emits output (so TimeoutExpired captures non-empty bytes) then
# sleeps past the timeout.
emit_then_sleep = [
    sys.executable,
    "-c",
    "import sys,time;"
    "sys.stdout.write('partial-out');sys.stdout.flush();"
    "sys.stderr.write('partial-err');sys.stderr.flush();"
    "time.sleep(5)",
]
cwd = pathlib.Path(".")


def check(result, label):
    assert result.exit_code == 124, f"{label}: expected exit 124, got {result.exit_code}"
    assert isinstance(result.stdout, str), f"{label}: stdout must be str, got {type(result.stdout)}"
    assert isinstance(result.stderr, str), f"{label}: stderr must be str, got {type(result.stderr)}"
    # The actual crash point in issue #6: serializing the raw turn.
    raw = broker._format_raw_turn(["x"], result, "the prompt text")
    json.loads(raw)  # must be valid JSON, not a TypeError


check(broker._run_command_with_input(emit_then_sleep, cwd=cwd, stdin="", timeout_s=1),
      "_run_command_with_input timeout")
check(broker._run_command(emit_then_sleep, 1), "_run_command timeout")

# A timed-out (124) turn must classify as a clean ParticipantFailed, not crash —
# so run_round records participant_failed instead of propagating an opaque error.
timed_out = broker.CommandResult(124, "partial", "timed out")
try:
    broker._classify_turn_failure("codex", timed_out)
except broker.ParticipantFailed as exc:
    assert exc.exit_code == 124, exc.exit_code
else:
    raise AssertionError("a timed-out (124) turn must raise ParticipantFailed")
PY

echo "harness_deliberation_timeout_test: PASS"
