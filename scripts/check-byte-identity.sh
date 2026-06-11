#!/usr/bin/env bash
# Self-host gate: foundry's own copies of verbatim templates must be
# byte-identical to plugins/foundry/templates/ (modulo the version-marker line).
# Usage: check-byte-identity.sh [repo-root]   (defaults to this repo)
set -euo pipefail
REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEMPLATES="$REPO/plugins/foundry/templates"
[ -d "$TEMPLATES" ] || { echo "byte-identity: PASS (no templates yet)"; exit 0; }

has_violation=0
while IFS= read -r -d '' template_file; do
  relative_path="${template_file#"$TEMPLATES/"}"
  repo_copy="$REPO/$relative_path"
  if ! grep -qvF 'foundry-template:' "$template_file"; then
    echo "byte-identity: EMPTY-TEMPLATE $relative_path (no content besides the marker)"
    has_violation=1
    continue
  fi
  if [ ! -f "$repo_copy" ]; then
    echo "byte-identity: MISSING $relative_path"
    has_violation=1
    continue
  fi
  if ! diff -q <(grep -vF 'foundry-template:' "$template_file") \
               <(grep -vF 'foundry-template:' "$repo_copy") >/dev/null; then
    echo "byte-identity: DRIFT $relative_path"
    has_violation=1
  fi
done < <(find "$TEMPLATES" -type f -print0)

[ "$has_violation" -eq 0 ] && echo "byte-identity: PASS"
exit "$has_violation"
