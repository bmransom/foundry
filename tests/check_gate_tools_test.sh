#!/usr/bin/env bash
# Discrimination test for check-gate-tools.sh (update-gate-sync US-5):
# a conventionVersion drift fails; the in-sync state passes; and the lint passes on
# Foundry itself (dogfood). The marker-wiring cases retired with T13 (pinned-run) when
# the `# foundry-gate-tool:` half of the lint was removed — no marked scripts remain.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINT="$HERE/../scripts/check-gate-tools.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

printf '| 3 | foo | x | y | z |\n' > "$tmp/registry-3.md"
printf '{ "conventionVersion": 3 }\n' > "$tmp/manifest-3.json"
printf '{ "conventionVersion": 4 }\n' > "$tmp/manifest-4.json"

run() { REGISTRY_FILE="$1" MANIFEST_FILE="$2" bash "$LINT" >/dev/null 2>&1; }

run "$tmp/registry-3.md" "$tmp/manifest-3.json" \
  || { echo "FAIL: a matching registry head + conventionVersion should pass"; exit 1; }

if run "$tmp/registry-3.md" "$tmp/manifest-4.json"; then
  echo "FAIL: registry-head != conventionVersion should fail the lint"; exit 1
fi

bash "$LINT" >/dev/null 2>&1 || { echo "FAIL: check-gate-tools should pass on Foundry itself"; exit 1; }

echo "check_gate_tools_test: PASS"
