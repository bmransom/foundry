#!/usr/bin/env bash
# Launch a same-harness successor seeded from a handoff briefing.
set -euo pipefail

readonly HANDOFF_PROMPT='Resume from a handoff. Read .agent/handoff/HANDOFF.md in full, then continue the Next unit of work, honoring the Guardrails. If .agent/handoff/HANDOFF.md is missing but .claude/handoff/HANDOFF.md exists, read the legacy Claude handoff and migrate any new handoff state to .agent/handoff/HANDOFF.md.'

main() {
  local runner_args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run|--skip-permissions|--yolo) runner_args+=("$1"); shift ;;
      --print-harness)
        exec "$(plugin_root)/scripts/spawn-fresh-session.sh" --print-harness
        ;;
      --) shift; break ;;
      -*) echo "spawn-successor: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done

  local slug="${1:?usage: spawn-successor.sh [--dry-run] [--skip-permissions] <slug> [project-dir]}"
  local dir="${2:-$PWD}"

  printf '%s\n' "$HANDOFF_PROMPT" |
    "$(plugin_root)/scripts/spawn-fresh-session.sh" ${runner_args[@]+"${runner_args[@]}"} --name "$slug" "$dir"
}

plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
