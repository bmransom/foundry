#!/usr/bin/env bash
# worktree-per-card: guard the "Done = merged" lifecycle wording across the
# contract docs AND the load-bearing lifecycle skill. The board conventions, the
# seed ROADMAP, AGENTS.md, the bootstrap generator, the `code` skill, and its
# worktree reference must state "Done = merged to the default branch" and must
# NOT regress to the old model — "Commit or push" (ask before every commit) or
# "Done requires a recorded gate PASS" / "Implemented and verified by a recorded
# gate PASS" (Done = gate-recorded / shipped).
#
# Discriminating on BOTH axes: a seeded forbidden phrase must be caught, and a
# doc stripped of the required phrase must fail — a guard that cannot fail
# asserts nothing.
# Hermetic: needs only grep, sed, and a tempfile.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { echo "FAIL: $1" >&2; exit 1; }

DOCS=(
  "$REPO/AGENTS.md"
  "$REPO/roadmap/ROADMAP.md"
  "$REPO/plugins/foundry/templates/seeds/roadmap/ROADMAP.md"
  "$REPO/plugins/foundry/skills/bootstrap/references/generate.md"
  "$REPO/plugins/foundry/skills/code/SKILL.md"
  "$REPO/plugins/foundry/skills/code/references/worktree.md"
)

# Old-model regression markers — none may appear in a contract doc. Precise on
# the Done definition so the new "the merged PR's gate run is the recorded gate
# PASS" explanation in worktree.md is NOT a false positive.
FORBIDDEN='Commit or push|requires a recorded gate PASS|Implemented and verified by a recorded gate PASS'
# New-model marker — every doc must state Done = merged.
REQUIRED='merge[sd]? to the default branch'

has_forbidden() { grep -nEq "$FORBIDDEN" "$1"; }
has_required()  { grep -qE  "$REQUIRED"  "$1"; }

# 1) No doc carries old-model wording.
for f in "${DOCS[@]}"; do
  [ -f "$f" ] || fail "missing contract doc: $f"
  ! has_forbidden "$f" || fail "$f regressed to old lifecycle wording (matched /$FORBIDDEN/)"
done

# 2) Every doc states Done = merged.
for f in "${DOCS[@]}"; do
  has_required "$f" || fail "$f does not state Done = merged (/$REQUIRED/)"
done

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

# 3a) Discrimination — a seeded forbidden phrase must be caught.
cp "$REPO/AGENTS.md" "$tmp"
printf '\n- Commit or push. Branch first on the default branch.\n' >> "$tmp"
! has_forbidden "$tmp" && fail "discrimination: scan failed to catch a seeded forbidden phrase"

# 3b) Discrimination — a doc stripped of the required phrase must fail step 2.
sed -E "s/$REQUIRED/REMOVED/g" "$REPO/AGENTS.md" > "$tmp"
has_required "$tmp" && fail "discrimination: scan failed to notice a missing Done=merged marker"

echo "done_merged_docs_test: PASS"
