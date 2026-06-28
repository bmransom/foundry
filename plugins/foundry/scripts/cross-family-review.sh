#!/usr/bin/env bash
# Shared cross-family review pass — the abstraction both review skills reuse.
#
# Derive the harness family complementary to the reviewer's (from the manifest), and —
# when one exists — spawn ONE context-isolated session on it with the given goal prompt,
# writing its report to <out>. Prints the family used on its last line, or "none"
# (single-family repo / no manifest / same family -> the caller runs single-agent).
#
# The COMBINE-RULE lives in the caller: code-review DROPs (precision), spec-review UNIONs
# (recall). This script owns only the shared mechanism — family derivation + the
# context-isolated spawn — so both skills share it with different goals/prompts.
#
# Usage: cross-family-review.sh <reviewer-family> <dir> <session-name> <out> <prompt>
# Test seam: CROSS_FAMILY_SPAWN_CMD <family> <out>  stubs the detached spawn (no tmux/LLM).
#            CROSS_FAMILY_OVERRIDE <family>         forces the complementary family.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_root="$(cd "$script_dir/.." && pwd)"            # scripts/ -> plugins/foundry
runner="$script_dir/spawn-fresh-session.sh"
family_deriver="$plugin_root/skills/code-review/scripts/refuter-family.sh"

reviewer_family="${1:?usage: cross-family-review.sh <reviewer-family> <dir> <name> <out> <prompt>}"
dir="${2:?dir required}"
name="${3:?session name required}"
out="${4:?out path required}"
prompt="${5:?prompt required}"

# Derive the complementary family. Skip (print "none") when there is none.
family="none"
if [ -n "${CROSS_FAMILY_OVERRIDE:-}" ]; then
  family="$CROSS_FAMILY_OVERRIDE"
elif [ -f "$dir/.foundry/manifest.json" ]; then
  family="$("$family_deriver" "$reviewer_family" "$dir/.foundry/manifest.json" 2>/dev/null || echo none)"
fi
if [ "$family" = none ] || [ -z "$family" ] || [ "$family" = "$reviewer_family" ]; then
  echo "none"
  exit 0
fi

# Spawn the context-isolated pass on the complementary family.
if [ -n "${CROSS_FAMILY_SPAWN_CMD:-}" ]; then
  "$CROSS_FAMILY_SPAWN_CMD" "$family" "$out"
else
  printf '%s\n' "$prompt" | AGENT_HARNESS="$family" "$runner" --name "$name" "$dir"
fi
echo "$family"
