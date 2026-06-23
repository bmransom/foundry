#!/usr/bin/env bash
# The `round` command's default per-turn budget must be high enough for a
# substantive critique turn, split from the cheap live-smoke probe's default.
# Evidence: real round turns were killed at the shared $0.25 default this session,
# and one even failed at $1.5. So `round` must default higher while `live-smoke`
# (a one-sentence probe) stays cheap. `--budget-usd` must still override.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$BROKER" ] || fail "missing broker script"

python3 - "$BROKER" <<'PY'
import importlib.util
import pathlib
import sys
import types

spec = importlib.util.spec_from_file_location("b", sys.argv[1])
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)

# The split must exist: a dedicated round default, higher than the probe default.
assert hasattr(broker, "DEFAULT_ROUND_BUDGET_USD"), "missing DEFAULT_ROUND_BUDGET_USD"
assert float(broker.DEFAULT_ROUND_BUDGET_USD) > float(
    broker.DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD
), "round default must exceed the live-smoke probe default"
assert float(broker.DEFAULT_ROUND_BUDGET_USD) >= 2.0, "round default too low (>=2.0)"

# Behavioral: `round` with no --budget-usd flows the round default to the runner.
captured = {}


class FakeStore:
    def __init__(self, name):
        self.session_id = name
        self.session = {"repo_root": "/tmp"}


broker.SessionStore.open = staticmethod(lambda d: FakeStore(pathlib.Path(d).name))
broker.run_start_preflight = lambda **k: types.SimpleNamespace(ok=True, failures=[])
broker.run_round = lambda **k: None


def fake_runner(repo, timeout_s, budget_usd):
    captured["budget"] = budget_usd
    return lambda *a, **k: None


broker._round_participant_runner = fake_runner

assert broker.main(["round", "--session-dir", "/tmp/sess"]) == 0
assert captured["budget"] == broker.DEFAULT_ROUND_BUDGET_USD, (
    f"round default should be {broker.DEFAULT_ROUND_BUDGET_USD}, got {captured['budget']}"
)

# Override still works.
broker.main(["round", "--session-dir", "/tmp/sess", "--budget-usd", "5.0"])
assert captured["budget"] == "5.0", f"--budget-usd override broken: {captured['budget']}"

# The live-smoke probe stays cheap — this is a split, not a global raise.
ls_cap = {}
broker.run_live_smoke = lambda **k: (
    ls_cap.update(b=k["claude_budget_usd"]) or {"session_dir": "/tmp", "finals": []}
)
broker.main(["live-smoke", "--session", "x"])
assert ls_cap["b"] == broker.DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD == "0.25", (
    f"live-smoke probe budget must stay 0.25, got {ls_cap['b']}"
)

print("round-budget split: PASS")
PY
echo "harness_deliberation_round_budget_test: PASS"
