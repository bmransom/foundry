#!/usr/bin/env bash
# T37: start --attach must honor AC-1.6 — attach only from an interactive
# terminal, otherwise derive is_interactive from sys.stdout.isatty() and print
# the exact `tmux attach -t <session>` command.
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
import contextlib
import importlib.util
import io
import pathlib
import sys

broker_path = pathlib.Path(sys.argv[1])
fixture_root = pathlib.Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("harness_deliberation_broker", broker_path)
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)

prompt = fixture_root / "prompt.md"
prompt.write_text("Design the broker.\n", encoding="utf-8")

# Capture the is_interactive main() resolves, without touching tmux or preflight.
recorded: dict[str, object] = {}


def fake_start_session(**kwargs):
    recorded.clear()
    recorded.update(kwargs)
    return broker.StartResult(
        session_dir=fixture_root / "session",
        tmux_session="foundry-hd-demo",
        tmux_commands=[],
        attach_command="tmux attach -t foundry-hd-demo",
    )


broker.start_session = fake_start_session


class FakeTty(io.StringIO):
    def isatty(self):
        return True


def run_start(stdout):
    with contextlib.redirect_stdout(stdout):
        rc = broker.main(
            [
                "start",
                "--attach",
                "--prompt",
                str(prompt),
                "--session",
                "demo",
                "--repo",
                str(fixture_root),
            ]
        )
    return rc, stdout.getvalue()


# Non-interactive stdout (a pipe / StringIO): must NOT auto-attach, must print
# the exact attach command.
rc, out = run_start(io.StringIO())
assert rc == 0, rc
assert recorded["is_interactive"] is False, recorded
assert recorded["attach"] is True, recorded
assert "tmux attach -t foundry-hd-demo" in out, repr(out)

# Interactive stdout (a tty): is_interactive must be True so start_session attaches.
rc, out = run_start(FakeTty())
assert rc == 0, rc
assert recorded["is_interactive"] is True, recorded

print("driver ok")
PY

echo "harness_deliberation_start_attach_test: PASS"
