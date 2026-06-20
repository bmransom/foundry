#!/usr/bin/env bash
# Start a harness-deliberation broker session.
set -euo pipefail

usage() {
  echo "usage: spawn-deliberation.sh [--dry-run] --prompt <prompt.md> --session <id> [--attach] [repo-root]" >&2
}

dry_run=0
attach=0
prompt=""
session=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --attach) attach=1; shift ;;
    --prompt)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      prompt="$2"
      shift 2
      ;;
    --session)
      [ "$#" -ge 2 ] || { usage; exit 2; }
      session="$2"
      shift 2
      ;;
    -*) echo "spawn-deliberation: unknown argument '$1'" >&2; usage; exit 2 ;;
    *) break ;;
  esac
done

[ -n "$prompt" ] || { usage; exit 2; }
[ -n "$session" ] || { usage; exit 2; }

repo="${1:-$PWD}"
plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
broker="$plugin_root/scripts/harness-deliberation-broker.py"

cmd=("$broker" start --prompt "$prompt" --session "$session" --repo "$repo")
[ "$attach" -eq 1 ] && cmd+=(--attach)

if [ "$dry_run" -eq 1 ]; then
  printf '%s' "${cmd[0]}"
  printf ' %s' "${cmd[@]:1}"
  printf '\n'
else
  exec "${cmd[@]}"
fi
