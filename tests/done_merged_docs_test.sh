#!/usr/bin/env bash
# worktree-per-card: guard the "Done = merged" lifecycle wording across the
# contract docs. The board conventions, the seed ROADMAP, AGENTS.md, and the
# bootstrap generator must state "Done = merged to the default branch" and must
# NOT regress to the old model — "Commit or push" (ask before every commit) or
# "Done requires a recorded gate PASS".
#
# Discriminating: a seeded regression (old wording reinserted) MUST make the
# scan fail — a guard that cannot fail asserts nothing.
# Hermetic: needs only grep + a tempfile.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { echo "FAIL: $1" >&2; exit 1; }

DOCS=(
  "$REPO/AGENTS.md"
  "$REPO/roadmap/ROADMAP.md"
  "$REPO/plugins/foundry/templates/seeds/roadmap/ROADMAP.md"
  "$REPO/plugins/foundry/skills/bootstrap/references/generate.md"
)

# Old-model regression markers — none may appear in a contract doc.
FORBIDDEN='Commit or push|recorded gate PASS'
# New-model marker — every contract doc must state Done = merged.
REQUIRED='merge[sd]? to the default branch'

has_forbidden() { grep -nEq "$FORBIDDEN" "$1"; }

# 1) No contract doc carries old-model wording.
for f in "${DOCS[@]}"; do
  [ -f "$f" ] || fail "missing contract doc: $f"
  ! has_forbidden "$f" || fail "$f regressed to old lifecycle wording (matched /$FORBIDDEN/)"
done

# 2) Every contract doc states Done = merged.
for f in "${DOCS[@]}"; do
  grep -qE "$REQUIRED" "$f" || fail "$f does not state Done = merged (/$REQUIRED/)"
done

# 3) Discrimination: a seeded regression must be caught by the same scan.
tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
cp "$REPO/AGENTS.md" "$tmp"
printf '\n- Commit or push. Branch first on the default branch.\n' >> "$tmp"
! has_forbidden "$tmp" && fail "discrimination: the scan failed to catch a seeded regression"

echo "done_merged_docs_test: PASS"
