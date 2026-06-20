#!/usr/bin/env bash
# Unit checks for harness-deliberation spec readiness gates.
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


session_dir = fixture_root / ".foundry/tmp/harness-deliberation/spec-demo"
store = broker.SessionStore.create(
    session_dir=session_dir,
    session_id="spec-demo",
    repo_root=fixture_root,
    base_commit="abc1234",
    participants=["codex", "claude-code"],
    config={"stall_rounds": 2},
)
broker.apply_decisions(
    session_dir=session_dir,
    questions=[{"question_id": "q0001", "text": "Which output shape?"}],
)

try:
    broker.check_spec_ready(session_dir=session_dir)
except ValueError as exc:
    assert "unresolved question" in str(exc)
    assert "q0001" in str(exc)
else:
    raise AssertionError("unresolved question should block spec")

broker.apply_decisions(
    session_dir=session_dir,
    decisions=[
        {
            "decision_id": "d0001",
            "question_id": "q0001",
            "disposition": "settled",
            "summary": "Write Foundry spec files.",
        }
    ],
)
(session_dir / "state.md").write_text("tampered\n", encoding="utf-8")
try:
    broker.check_spec_ready(session_dir=session_dir)
except ValueError as exc:
    assert "tier 3 view differs" in str(exc)
    assert "state.md" in str(exc)
else:
    raise AssertionError("dirty rebuild should block spec")

store.render_views()
state = broker.check_spec_ready(session_dir=session_dir)
assert_equal(state["open_questions"], [], "closed state")
PY

echo "harness_deliberation_spec_test: PASS"
