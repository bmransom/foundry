#!/usr/bin/env bash
# Launch a same-harness skill drafting session from a brief.
set -euo pipefail

main() {
  local runner_args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) runner_args+=("$1"); shift ;;
      --print-harness)
        exec "$(plugin_root)/scripts/spawn-fresh-session.sh" --print-harness
        ;;
      --) shift; break ;;
      -*) echo "spawn-extractor: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done

  local skill="${1:?usage: spawn-extractor.sh [--dry-run] <skill-name> <brief-path> [project-dir]}"
  local brief="${2:?usage: spawn-extractor.sh [--dry-run] <skill-name> <brief-path> [project-dir]}"
  local dir="${3:-$PWD}"
  local slug="extract-$skill"
  # Absolute draft path under the PRIMARY tree, so retiring the spawned
  # session's worktree cannot delete the draft (the harness cwd is the
  # worktree after isolation).
  local draft="$dir/.agent/skill-extractions/$skill/draft-SKILL.md"
  local prompt="Read $brief in full. Draft or revise the skill described there using the Agent Skills format. Preserve reusable procedure, exclude non-reusable details, add realistic eval prompts, validate the structure. Write the draft to the absolute path $draft, then report back."

  printf '%s\n' "$prompt" |
    "$(plugin_root)/scripts/spawn-fresh-session.sh" ${runner_args[@]+"${runner_args[@]}"} --name "$slug" "$dir"
}

plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
