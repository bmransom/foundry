#!/usr/bin/env bash
# The deliberation tmux session is a pure VIEWER: codex | claude side-by-side, plus a
# transcript window. Mediation is chat-based (the broker `decide` driven from the chat),
# so there is no mediator pane to hand-type commands into.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$BROKER" ] || fail "missing broker script"

python3 - "$BROKER" <<'PY'
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location("b", sys.argv[1])
broker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(broker)

commands = broker.build_tmux_commands(
    repo_root=Path("/repo"),
    session_dir=Path("/sess"),
    tmux_session="foundry-hd-x",
)
joined = [" ".join(map(str, c)) for c in commands]

# Exactly one split — codex | claude side-by-side, horizontal — and no vertical split.
splits = [c for c in commands if "split-window" in c]
assert len(splits) == 1, f"expected 1 split (codex|claude side-by-side), got {len(splits)}"
assert "-h" in splits[0], "the participant split must be horizontal (side-by-side)"
assert not any("-v" in c for c in commands), "no vertical mediator split"

# Both participants are present as viewer panes.
assert any("codex" in j for j in joined), "codex pane missing"
assert any("claude" in j for j in joined), "claude pane missing"

# The mediator pane is gone — mediation is chat-based.
assert not hasattr(broker, "_mediator_pane_command"), "remove _mediator_pane_command (chat mediation)"
assert not any("FOUNDRY_HD_SESSION" in j for j in joined), "no mediator shell pane"
assert not any("broker commands" in j for j in joined), "no mediator help pane"

# The transcript window still tails the running deliberation.
assert any("tail -f" in j for j in joined), "transcript window missing"

print("pane-layout (codex | claude viewer, chat mediation): PASS")
PY
echo "harness_deliberation_pane_layout_test: PASS"
