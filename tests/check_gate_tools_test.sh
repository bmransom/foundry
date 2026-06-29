#!/usr/bin/env bash
# Discrimination test for check-gate-tools.sh (update-gate-sync US-5):
# an unwired marked tool fails; a conventionVersion drift fails; the wired/in-sync
# state passes; and the lint passes on Foundry itself (dogfood).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LINT="$HERE/../scripts/check-gate-tools.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/scripts"
printf '#!/usr/bin/env python3\n# foundry-gate-tool: python3 scripts/widget.py\nprint("hi")\n' > "$tmp/scripts/widget.py"
printf 'python3 scripts/widget.py\n' > "$tmp/gate-wired.sh"
printf 'echo no tools here\n' > "$tmp/gate-unwired.sh"
printf '| 3 | foo | x | y | z |\n' > "$tmp/registry-3.md"
printf '{ "conventionVersion": 3 }\n' > "$tmp/manifest-3.json"
printf '{ "conventionVersion": 4 }\n' > "$tmp/manifest-4.json"

run() { GATE_FILE="$1" SCRIPTS_DIR="$2" REGISTRY_FILE="$3" MANIFEST_FILE="$4" bash "$LINT" >/dev/null 2>&1; }

run "$tmp/gate-wired.sh" "$tmp/scripts" "$tmp/registry-3.md" "$tmp/manifest-3.json" \
  || { echo "FAIL: a wired tool + matching conventionVersion should pass"; exit 1; }

if run "$tmp/gate-unwired.sh" "$tmp/scripts" "$tmp/registry-3.md" "$tmp/manifest-3.json"; then
  echo "FAIL: an unwired marked tool should fail the lint"; exit 1
fi

if run "$tmp/gate-wired.sh" "$tmp/scripts" "$tmp/registry-3.md" "$tmp/manifest-4.json"; then
  echo "FAIL: registry-head != conventionVersion should fail the lint"; exit 1
fi

bash "$LINT" >/dev/null 2>&1 || { echo "FAIL: check-gate-tools should pass on Foundry itself"; exit 1; }

echo "check_gate_tools_test: PASS"
