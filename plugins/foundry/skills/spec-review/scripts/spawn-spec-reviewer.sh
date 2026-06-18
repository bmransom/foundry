#!/usr/bin/env bash
# Launch a same-harness fresh-context spec review.
set -euo pipefail

usage() {
  echo "usage: spawn-spec-reviewer.sh [--dry-run] [--skip-permissions] <target> [project-dir]" >&2
}

main() {
  local dry_run=0 runner_args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1; runner_args+=("$1"); shift ;;
      --print-harness)
        exec "$(plugin_root)/scripts/spawn-fresh-session.sh" --print-harness
        ;;
      --skip-permissions|--yolo) runner_args+=("$1"); shift ;;
      --) shift; break ;;
      -*) echo "spawn-spec-reviewer: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done

  [ "$#" -ge 1 ] || { usage; exit 2; }
  local target="$1"
  local dir="${2:-$PWD}"
  local review_dir=".foundry/reports/spec-review"
  local report="$review_dir/$(date +%Y%m%d%H%M%S)-spec-review.md"
  local prompt="Use the spec-review skill to review $target in fresh context. Read knowledge/glossary.md and the AGENTS.md Writing style section first. Return findings only: location, problem, concrete fix, clean-file notes, and the highest-priority fix. Write the complete report to $report."
  [ "$dry_run" -eq 1 ] || mkdir -p "$dir/$review_dir"

  printf '%s\n' "$prompt" |
    "$(plugin_root)/scripts/spawn-fresh-session.sh" ${runner_args[@]+"${runner_args[@]}"} --name spec-review "$dir"
  echo "report: $report"
}

plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
