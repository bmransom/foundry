#!/usr/bin/env bash
# Hermetic checks for the triggering-eval runner. Exercises --dry-run and
# --grade-only only, so it passes with `claude` ABSENT and never spawns a model.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
RUNNER="$REPO/evals/harness/triggering-eval.sh"
CASES="$REPO/evals/fixtures/triggering/cases.json"
RESULTS_DIR="$REPO/evals/results"

fail() { echo "FAIL: $1" >&2; exit 1; }

[ -x "$RUNNER" ] || fail "triggering-eval.sh must exist and be executable"

# The gitignored results dir may not exist on a fresh checkout (e.g. CI); create it
# so the `find` below cannot abort the test under set -e + pipefail with a swallowed error.
mkdir -p "$RESULTS_DIR"

# --- dry-run: builds the prompt from live descriptions, spawns nothing --------
before="$(find "$RESULTS_DIR" -name 'triggering-*' 2>/dev/null | wc -l | tr -d ' ')"
dry="$("$RUNNER" --dry-run)"
case "$dry" in *"skills: "*"## Answer"*) ;; *) fail "dry-run must print the skill count and prompt" ;; esac
echo "$dry" | grep -q "Use when" || fail "dry-run prompt must carry the live skill descriptions"
echo "$dry" | grep -q "p99" || fail "dry-run prompt must embed the first case's query"
after="$(find "$RESULTS_DIR" -name 'triggering-*' 2>/dev/null | wc -l | tr -d ' ')"
[ "$before" = "$after" ] || fail "dry-run must not write result files"

# --- grade-only: perfect predictions pass, a wrong one fails ------------------
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
python3 -c "
import json
cases = json.load(open('$CASES'))['cases']
json.dump([{'id': c['id'], 'predicted': c['expect']} for c in cases], open('$TMP/perfect.json', 'w'))
flipped = [{'id': c['id'], 'predicted': ('NONE' if c['expect'] != 'NONE' else 'code')} for c in cases]
json.dump(flipped, open('$TMP/wrong.json', 'w'))
"
"$RUNNER" --grade-only "$TMP/perfect.json" >/dev/null || fail "perfect predictions should grade as pass"
if "$RUNNER" --grade-only "$TMP/wrong.json" >/dev/null 2>&1; then fail "wrong predictions should fail the grade"; fi

echo "triggering_eval_test: PASS"
