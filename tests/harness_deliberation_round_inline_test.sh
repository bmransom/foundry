#!/usr/bin/env bash
# round-inline.sh runs a deliberation round with two ephemeral viewer panes
# (codex | claude) ABOVE the host pane and closes them on exit — even if the round
# fails. The tail loop comes from the broker's `pane-command` (one source).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"
WRAPPER="$REPO/plugins/foundry/skills/harness-deliberation/scripts/round-inline.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$BROKER" ] || fail "missing broker"
[ -f "$WRAPPER" ] || fail "missing round-inline.sh"

# 1) pane-command prints a long-lived viewer tail of each actor's final.md.
codex_cmd="$(python3 "$BROKER" pane-command --session-dir /sess --actor codex)"
claude_cmd="$(python3 "$BROKER" pane-command --session-dir /sess --actor claude-code)"
case "$codex_cmd" in *codex*final.md*) ;; *) fail "codex pane-command lacks codex/final.md: $codex_cmd" ;; esac
case "$claude_cmd" in *claude*final.md*) ;; *) fail "claude pane-command lacks claude/final.md" ;; esac
python3 "$BROKER" pane-command --session-dir /sess --actor bogus >/dev/null 2>&1 \
  && fail "pane-command accepted an unknown actor" || true

# 2) Outside tmux (no host pane), refuse loudly — don't silently no-op.
if env -u TMUX -u TMUX_PANE FOUNDRY_HD_HOST_PANE="" bash "$WRAPPER" --session-dir /sess >/dev/null 2>&1; then
  fail "round-inline must refuse with no host pane"
fi

# 3) With a stub tmux, it splits two panes above the host and kills both on exit,
#    even though the round fails (nonexistent session) — cleanup-on-failure.
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
export TMUX_LOG="$work/tmux.log"
cat > "$work/tmux" <<'STUB'
#!/usr/bin/env bash
echo "$*" >> "$TMUX_LOG"
if [ "$1" = "split-window" ]; then
  printf '%%fake%s\n' "$(grep -c 'split-window' "$TMUX_LOG")"
fi
exit 0
STUB
chmod +x "$work/tmux"

PATH="$work:$PATH" bash "$WRAPPER" --session-dir "$work/no-such-session" --host-pane "%host" \
  >/dev/null 2>&1 || true  # the round fails on the missing session; the trap must still fire

log="$(cat "$TMUX_LOG")"
[ "$(grep -c 'split-window' "$TMUX_LOG")" -eq 2 ] || fail "expected 2 split-window calls, got: $log"
case "$log" in *"-b -v"*) ;; *) fail "first split must be above the host (-b -v): $log" ;; esac
case "$log" in *"-t %host"*) ;; *) fail "first split must target the host pane: $log" ;; esac
case "$log" in *"-t %fake1"*) ;; *) fail "claude split must target the codex pane id: $log" ;; esac
[ "$(grep -c 'kill-pane' "$TMUX_LOG")" -eq 2 ] || fail "panes not cleaned up on failure: $log"
case "$log" in *"kill-pane -t %fake1"*) ;; *) fail "codex pane not killed: $log" ;; esac
case "$log" in *"kill-pane -t %fake2"*) ;; *) fail "claude pane not killed: $log" ;; esac

echo "harness_deliberation_round_inline_test: PASS"
