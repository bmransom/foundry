#!/usr/bin/env bash
# Self-host lint (update-gate-sync US-5): the migration registry head must equal the
# manifest conventionVersion — a convention can't ship without its migration row.
# The `# foundry-gate-tool:` marker-wiring half retired with T13 (pinned-run): the gate
# suite is code in foundry.gate/*, no vendored marked scripts remain to wire.
# Foundry-local — NOT a verbatim template, and NOT in the shipped code-review skill
# (mechanisms-not-content). Env seams (REGISTRY_FILE / MANIFEST_FILE) let the test drive
# it against fixtures.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGISTRY_FILE="${REGISTRY_FILE:-$REPO/src/foundry/materializer/migrations/README.md}"
MANIFEST_FILE="${MANIFEST_FILE:-$REPO/.foundry/manifest.json}"

fail=0

# Registry head == manifest conventionVersion.
head_conv="$(grep -oE '^\| [0-9]+ ' "$REGISTRY_FILE" | grep -oE '[0-9]+' | sort -n | tail -1)"
manifest_conv="$(grep -oE '"conventionVersion"[[:space:]]*:[[:space:]]*[0-9]+' "$MANIFEST_FILE" | grep -oE '[0-9]+')"
if [ -n "$head_conv" ] && [ "$head_conv" != "$manifest_conv" ]; then
  echo "check-gate-tools: registry head ($head_conv) != manifest conventionVersion ($manifest_conv) — a convention shipped without its migration row" >&2
  fail=1
fi

[ "$fail" -eq 0 ] || exit 1
echo "check-gate-tools: PASS"
