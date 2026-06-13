#!/usr/bin/env bash
# Headless lifecycle eval (Layer 3): drive the foundry code lifecycle skill
# through one small NEW FEATURE (a --version flag) end-to-end under canned
# approvals, then grade the artifacts each stage leaves behind — never the
# agent's self-report (AC-5.3). A smoke alarm, run once per version bump.
#
# Usage:
#   evals/harness/lifecycle-eval.sh <bootstrapped-tree> [feature-keyword]
#   evals/harness/lifecycle-eval.sh --grade-only <tree> <snapshot-sha> <log>
#
# <bootstrapped-tree>  a tree already bootstrapped with the foundry setup; the
#                      eval works in it and grades against HEAD-before-the-run.
# feature-keyword      board-row keyword the grader looks for (default: version).
# --grade-only         skip the headless claude call; re-grade an existing run.
#
# Results: NDJSON in evals/results/lifecycle-<epoch>.ndjson; the full claude
# transcript and gate output in evals/results/lifecycle-<epoch>.log. The
# transcript is retained on FAIL.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"
SKILL="$FOUNDRY_REPO/plugins/foundry/skills/code/SKILL.md"

GRADE_ONLY=0
DEFAULT_KEYWORD="version"

usage() { sed -n '2,21p' "${BASH_SOURCE[0]}"; exit 2; }

preflight() { # tree — fail fast (exit 2) unless the tree is a clean bootstrapped repo
  local tree="$1" path
  [ -d "$tree" ] || { echo "lifecycle-eval: tree not found: $tree" >&2; exit 2; }
  for path in AGENTS.md docs/ROADMAP.md scripts/check-fast.sh; do
    [ -f "$tree/$path" ] || { echo "lifecycle-eval: missing $path — bootstrap the tree first" >&2; exit 2; }
  done
  for path in specs features; do
    [ -d "$tree/$path" ] || { echo "lifecycle-eval: missing $path/ — bootstrap the tree first" >&2; exit 2; }
  done
  git -C "$tree" rev-parse --git-dir >/dev/null 2>&1 \
    || { echo "lifecycle-eval: $tree is not a git repo" >&2; exit 2; }
  [ -z "$(git -C "$tree" status --porcelain)" ] \
    || { echo "lifecycle-eval: $tree has a dirty git tree — commit or stash first" >&2; exit 2; }
}

grade() { # tree snapshot log keyword results — tee NDJSON; return the grader's status
  local tree="$1" snapshot="$2" log="$3" keyword="$4" results="$5" status=0
  python3 "$HARNESS/grade_lifecycle.py" "$tree" "$snapshot" "$log" \
    --keyword "$keyword" --results "$results" || status=$?
  return "$status"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --grade-only) GRADE_ONLY=1; shift ;;
    -h|--help) usage ;;
    *) break ;;
  esac
done

mkdir -p "$RESULTS_DIR"
stamp="$(date +%s)"
results="$RESULTS_DIR/lifecycle-$stamp.ndjson"

if [ "$GRADE_ONLY" -eq 1 ]; then
  [ "$#" -eq 3 ] || usage
  tree="$1"; snapshot="$2"; log="$3"
  [ -f "$log" ] || { echo "lifecycle-eval: log not found: $log" >&2; exit 2; }
  echo "lifecycle-eval: grade-only tree=$tree snapshot=$snapshot log=$log results=$results"
  if grade "$tree" "$snapshot" "$log" "$DEFAULT_KEYWORD" "$results"; then
    echo "lifecycle-eval: PASS"
  else
    echo "lifecycle-eval: FAIL"
    exit 1
  fi
  exit
fi

[ "$#" -ge 1 ] && [ "$#" -le 2 ] || usage
tree="$(cd "$1" && pwd)"
keyword="${2:-$DEFAULT_KEYWORD}"
log="$RESULTS_DIR/lifecycle-$stamp.log"

preflight "$tree"
snapshot="$(git -C "$tree" rev-parse HEAD)"
echo "lifecycle-eval: tree=$tree snapshot=$snapshot keyword=$keyword"
echo "lifecycle-eval: log=$log"
echo "lifecycle-eval: results=$results"

prompt="Use the foundry code lifecycle skill at $SKILL — read it and follow it exactly, treating this as a NEW FEATURE (all stages). Feature: add a \`--version\` flag (or version endpoint) that prints the project version. Canned approvals: design approved as proposed; plan approved as proposed; yes, commit at Finish. Work in the current repo."

echo "lifecycle-eval: running headless lifecycle (this takes minutes)"
run_failed=0
if (cd "$tree" && claude -p "$prompt" \
    --plugin-dir "$FOUNDRY_REPO/plugins/foundry" \
    --dangerously-skip-permissions \
    --verbose --output-format stream-json) >"$log" 2>&1; then
  echo "lifecycle-eval: headless run completed"
else
  echo "lifecycle-eval: claude -p exited nonzero — see the log" >&2
  run_failed=1
fi

if grade "$tree" "$snapshot" "$log" "$keyword" "$results"; then
  grade_failed=0
else
  grade_failed=1
fi

if [ "$run_failed" -eq 0 ] && [ "$grade_failed" -eq 0 ]; then
  echo "lifecycle-eval: PASS"
else
  echo "lifecycle-eval: transcript retained at $log"
  echo "lifecycle-eval: FAIL"
  exit 1
fi
