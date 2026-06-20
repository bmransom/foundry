#!/usr/bin/env bash
# Headless code-review eval (Layer 3): run the code-review skill over the seeded
# fixture N times, then score recall and decoy hits mechanically against the
# answer key via score_review.py (UNCHANGED). Honest framing: at affordable N
# this is a smoke alarm for large regressions, not statistics.
#
# Usage:
#   evals/harness/code-review-eval.sh [N]                       (default N=3 runs)
#   evals/harness/code-review-eval.sh --score-only <findings.txt>
#   evals/harness/code-review-eval.sh --score-ab <A.txt> <B.txt> (reviewer vs reviewer+refuter)
#
# --score-only  skip the headless review; score one findings text file.
# --score-ab    score Arm A (reviewer-alone) and Arm B (reviewer+refuter) with the
#               same answer key; enable the refuter by default ONLY if Arm B holds
#               mean recall >= 4/5 AND decoy hits = 0, else disable it.
#
# Scoring reads only the findings text — a transcript echoes the code under
# review, so every signature would match. The skill under test is
# plugins/foundry/skills/code-review/SKILL.md, never a removed agent file.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
FIXTURE_DIR="$FOUNDRY_REPO/evals/fixtures/code-review"
TREE="$FIXTURE_DIR/tree"
ANSWER_KEY="$FIXTURE_DIR/answer-key.json"
REVIEW_SKILL="$FOUNDRY_REPO/plugins/foundry/skills/code-review/SKILL.md"
if [ ! -f "$REVIEW_SKILL" ]; then
  echo "code-review-eval: missing review skill $REVIEW_SKILL" >&2
  exit 1
fi
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

usage() { sed -n '2,19p' "${BASH_SOURCE[0]}"; exit 2; }

extract_findings() { # stream-json log -> the final result text on stdout
  python3 - "$1" <<'PY'
import json, sys

findings = ""
with open(sys.argv[1], encoding="utf-8", errors="replace") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") == "result":
            findings = record.get("result") or ""
print(findings)
PY
}

# Score one arm: print the summary line and return the scorer's verdict status.
# Usage: score_arm <label> <results.ndjson> <findings.txt>...
score_arm() {
  local label="$1" results="$2"; shift 2
  local scorer_status=0 score_output summary_fields verdict mean_recall decoy_hits
  score_output="$(python3 "$HARNESS/score_review.py" "$ANSWER_KEY" "$@" --results "$results")" \
    || scorer_status=$?
  printf '%s\n' "$score_output"
  summary_fields="$(printf '%s\n' "$score_output" | python3 -c '
import json, sys

summary = {}
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    record = json.loads(line)
    if record.get("event") == "summary":
        summary = record
print(
    str(summary.get("verdict", "fail")).upper(),
    summary.get("mean_recall", "n/a"),
    summary.get("decoy_hits", "n/a"),
)
')"
  read -r verdict mean_recall decoy_hits <<<"$summary_fields"
  echo "code-review-eval: $label $verdict mean_recall=$mean_recall decoys=$decoy_hits"
  return "$scorer_status"
}

# A/B gating (T13): enable the refuter ONLY if Arm B holds the bar.
score_ab() {
  local a_findings="$1" b_findings="$2"
  local stamp results_a results_b a_status=0 b_status=0
  stamp="$(date +%s)"
  results_a="$RESULTS_DIR/code-review-$stamp-armA.ndjson"
  results_b="$RESULTS_DIR/code-review-$stamp-armB.ndjson"
  echo "code-review-eval: A/B armA=$a_findings armB=$b_findings"
  score_arm "armA (reviewer-alone)" "$results_a" "$a_findings" || a_status=$?
  score_arm "armB (reviewer+refuter)" "$results_b" "$b_findings" || b_status=$?
  if [ "$b_status" -eq 0 ]; then
    echo "code-review-eval: refuter ENABLED by default — armB holds mean recall >= 4/5 AND decoy hits = 0"
    return 0
  fi
  echo "code-review-eval: refuter DISABLED — armB fell below the bar; reviewer runs single-agent"
  return 1
}

mkdir -p "$RESULTS_DIR"

case "${1:-}" in
  --score-only)
    [ "$#" -eq 2 ] && [ -f "$2" ] || usage
    stamp="$(date +%s)"
    results="$RESULTS_DIR/code-review-$stamp.ndjson"
    echo "code-review-eval: score-only findings=$2 results=$results"
    score_arm "score-only" "$results" "$2"
    exit
    ;;
  --score-ab)
    [ "$#" -eq 3 ] && [ -f "$2" ] && [ -f "$3" ] || usage
    score_ab "$2" "$3"
    exit
    ;;
  -h|--help) usage ;;
esac

[ "$#" -le 1 ] || usage
RUNS="${1:-3}"
case "$RUNS" in (*[!0-9]*|"") usage ;; esac
[ "$RUNS" -ge 1 ] || usage

stamp="$(date +%s)"
results="$RESULTS_DIR/code-review-$stamp.ndjson"
echo "code-review-eval: runs=$RUNS tree=$TREE"
echo "code-review-eval: results=$results"

prompt="Read $REVIEW_SKILL and follow it exactly. Review the order-sync change in roadmap/specs/order-sync against the working tree (src/, tests/, docs/, generated/). This is READ-ONLY. After the findings, output a footer block — one line per flagged item in the form: FLAGGED: <the exact offending term, identifier, AC id, or quoted phrase>. Include FLAGGED lines for flagged items only — anything correct must NOT appear in a FLAGGED line. End with a single final line: CODE_REVIEW: PASS or CODE_REVIEW: FAIL."
findings_files=()
for ((run_number = 1; run_number <= RUNS; run_number++)); do
  log="$RESULTS_DIR/code-review-$stamp-run$run_number.log"
  findings="$RESULTS_DIR/code-review-$stamp-run$run_number.findings.txt"
  echo "code-review-eval: run $run_number/$RUNS — headless review (this takes minutes), log=$log"
  if (cd "$TREE" && claude -p "$prompt" \
      --dangerously-skip-permissions \
      --verbose --output-format stream-json) >"$log" 2>&1; then
    echo "code-review-eval: run $run_number completed"
  else
    echo "code-review-eval: run $run_number — claude -p exited nonzero; empty findings score zero recall" >&2
  fi
  extract_findings "$log" >"$findings"
  findings_files+=("$findings")
done

score_arm "headless" "$results" "${findings_files[@]}"
