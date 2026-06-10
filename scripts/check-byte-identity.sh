#!/usr/bin/env bash
# Self-host gate: foundry's own copies of verbatim templates must be
# byte-identical to plugins/foundry/templates/ (modulo the version-marker line).
# Usage: check-byte-identity.sh [repo-root]   (defaults to this repo)
set -euo pipefail
REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEMPLATES="$REPO/plugins/foundry/templates"
[ -d "$TEMPLATES" ] || { echo "byte-identity: PASS (no templates yet)"; exit 0; }

fail=0
while IFS= read -r -d '' template_file; do
  relative_path="${template_file#"$TEMPLATES/"}"
  repo_copy="$REPO/$relative_path"
  if [ ! -f "$repo_copy" ]; then
    echo "byte-identity: MISSING $relative_path"
    fail=1
    continue
  fi
  if ! diff -q <(grep -v 'foundry-template:' "$template_file") \
               <(grep -v 'foundry-template:' "$repo_copy") >/dev/null; then
    echo "byte-identity: DRIFT $relative_path"
    fail=1
  fi
done < <(find "$TEMPLATES" -type f -print0)

[ "$fail" -eq 0 ] && echo "byte-identity: PASS"
exit "$fail"
