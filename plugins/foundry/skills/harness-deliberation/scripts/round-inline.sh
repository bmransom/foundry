#!/usr/bin/env bash
# Run a deliberation round with two ephemeral viewer panes — codex | claude —
# ABOVE the current pane, then close them when the round finishes.
#
# Use from inside a tmux pane (e.g. an active Claude Code session): the
# deliberation appears above your chat and vanishes on completion, so mediation
# stays here in the chat and there is no separate session to switch to. A `trap`
# closes the panes even if the round errors or is interrupted.
set -euo pipefail

usage() {
  echo "usage: round-inline.sh --session-dir <dir> [--host-pane <id>] [round args...]" >&2
}

session_dir=""
host="${FOUNDRY_HD_HOST_PANE:-${TMUX_PANE:-}}"
round_args=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session-dir) session_dir="${2:-}"; shift 2 ;;
    --host-pane) host="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) round_args+=("$1"); shift ;;
  esac
done

[ -n "$session_dir" ] || { usage; exit 2; }
[ -n "$host" ] || {
  echo "round-inline: not inside tmux (no TMUX_PANE) — run a plain 'round', or pass --host-pane" >&2
  exit 2
}

plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
broker="$plugin_root/scripts/harness-deliberation-broker.py"

# One source for the tail loop (the broker), so the inline view never drifts from
# the separate-session layout.
codex_cmd="$("$broker" pane-command --session-dir "$session_dir" --actor codex)"
claude_cmd="$("$broker" pane-command --session-dir "$session_dir" --actor claude-code)"

# Split codex above the host pane, then claude to its right → codex | claude.
top="$(tmux split-window -b -v -l 45% -P -F '#{pane_id}' -t "$host" "$codex_cmd")"
right="$(tmux split-window -h -P -F '#{pane_id}' -t "$top" "$claude_cmd")"

cleanup() {
  tmux kill-pane -t "$top" 2>/dev/null || true
  tmux kill-pane -t "$right" 2>/dev/null || true
}
trap cleanup EXIT

if [ "${#round_args[@]}" -gt 0 ]; then
  "$broker" round --session-dir "$session_dir" "${round_args[@]}"
else
  "$broker" round --session-dir "$session_dir"
fi
