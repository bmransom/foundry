#!/usr/bin/env bash
# Pick the cross-model refuter's harness family: a family from the manifest that is
# NOT the reviewer's, so the refuter runs on a different model lineage (AC-9.5,
# AC-13.1). Families come from the manifest `harnesses` set, normalized to family
# tokens (claude-code -> claude). One family only -> "none" (skip the refuter; run the
# reviewer single-agent). Pure selection — no spawn, no model calls.
# Usage: refuter-family.sh <reviewer-family> <manifest.json>
set -euo pipefail

reviewer="${1:?usage: refuter-family.sh <reviewer-family> <manifest.json>}"
manifest="${2:?manifest path required}"
[ -f "$manifest" ] || { echo "refuter-family: no manifest at $manifest" >&2; exit 2; }

reviewer="$(printf '%s' "$reviewer" | sed 's/^claude-code$/claude/')"
families="$(grep -oE '"(claude-code|codex|claude)"' "$manifest" \
  | tr -d '"' | sed 's/^claude-code$/claude/' | sort -u)"

for fam in $families; do
  if [ "$fam" != "$reviewer" ]; then printf '%s\n' "$fam"; exit 0; fi
done
echo "none"
