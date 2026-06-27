#!/usr/bin/env bash
# Tracer bullet (T32): the cross-harness refuter handoff. The refuter must run on a
# DIFFERENT harness family than the reviewer (cross-model), selected from the manifest;
# and it receives ONLY the FLAGGED footer + diff, never the reviewer's prose or verdict.
# Hermetic — no spawn, no model calls.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RF="$REPO/plugins/foundry/skills/code-review/scripts/refuter-family.sh"
ALG="$REPO/plugins/foundry/skills/code-review/scripts/footer-algebra.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$RF" ] || fail "missing/!executable refuter-family.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

mf="$work/manifest.json"
printf '%s\n' '{"harnesses": ["claude-code", "codex"], "files": {}}' > "$mf"
[ "$("$RF" claude "$mf")"      = "codex"  ] || fail "claude reviewer -> codex refuter"
[ "$("$RF" codex  "$mf")"      = "claude" ] || fail "codex reviewer -> claude refuter"
[ "$("$RF" claude-code "$mf")" = "codex"  ] || fail "claude-code (normalized) -> codex refuter"

# single-family manifest -> no refuter (skip; run the reviewer single-agent).
printf '%s\n' '{"harnesses": ["claude-code"], "files": {}}' > "$work/solo.json"
[ "$("$RF" claude "$work/solo.json")" = "none" ] || fail "single family -> none"

# footer-only handoff: the refuter's payload is the union (FLAGGED-only) — never prose/verdict.
printf '## reviewer private reasoning\nFLAGGED: AC-2.1\nFLAGGED: db.py:7 raw print\nCODE_REVIEW: FAIL\n' > "$work/report"
payload="$("$ALG" union "$work/report")"
grep -q '^FLAGGED:' <<<"$payload" || fail "handoff: payload must carry the FLAGGED footer"
grep -q 'reasoning'  <<<"$payload" && fail "handoff: payload must NOT carry the reviewer's prose"
grep -q 'CODE_REVIEW:' <<<"$payload" && fail "handoff: payload must NOT carry the verdict line"

echo "code_review_refuter_family_test: PASS"
