#!/usr/bin/env bash
# Self-host lint (update-gate-sync US-5): catch gate-tool drift in Foundry itself —
#   1. every `# foundry-gate-tool:`-marked script under scripts/ is wired into the gate,
#   2. the migration registry head equals the manifest conventionVersion.
# Foundry-local — NOT a verbatim template, and NOT in the shipped code-review skill
# (mechanisms-not-content). Env seams (GATE_FILE / SCRIPTS_DIR / REGISTRY_FILE /
# MANIFEST_FILE) let the test drive it against fixtures.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GATE_FILE="${GATE_FILE:-$REPO/scripts/check-fast.sh}"
SCRIPTS_DIR="${SCRIPTS_DIR:-$REPO/scripts}"
REGISTRY_FILE="${REGISTRY_FILE:-$REPO/plugins/foundry/skills/update/references/migrations/README.md}"
MANIFEST_FILE="${MANIFEST_FILE:-$REPO/.foundry/manifest.json}"

fail=0

# 1. Every marked gate tool is referenced in the gate.
while IFS= read -r script; do
  base="$(basename "$script")"
  if ! grep -qF "$base" "$GATE_FILE"; then
    echo "check-gate-tools: $base carries a foundry-gate-tool marker but is not wired into $(basename "$GATE_FILE")" >&2
    fail=1
  fi
done < <(grep -rlE '^# foundry-gate-tool:' "$SCRIPTS_DIR" 2>/dev/null || true)

# 2. Registry head == manifest conventionVersion.
head_conv="$(grep -oE '^\| [0-9]+ ' "$REGISTRY_FILE" | grep -oE '[0-9]+' | sort -n | tail -1)"
manifest_conv="$(grep -oE '"conventionVersion"[[:space:]]*:[[:space:]]*[0-9]+' "$MANIFEST_FILE" | grep -oE '[0-9]+')"
if [ -n "$head_conv" ] && [ "$head_conv" != "$manifest_conv" ]; then
  echo "check-gate-tools: registry head ($head_conv) != manifest conventionVersion ($manifest_conv) — a convention shipped without its migration row" >&2
  fail=1
fi

[ "$fail" -eq 0 ] || exit 1
echo "check-gate-tools: PASS"
