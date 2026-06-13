#!/usr/bin/env bash
# Headless reviewer eval (Layer 3): run the spec-reviewer agent over the
# seeded fixture N times, then score recall and decoy hits mechanically
# against the answer key (AC-5.3). Honest framing per design §Evals: at
# affordable N this is a smoke alarm for large regressions, not statistics.
#
# Usage:
#   evals/harness/reviewer-eval.sh [N]                 (default N=3 runs)
#   evals/harness/reviewer-eval.sh --score-only <findings.txt>
#
# --score-only  skip the headless claude calls; score one findings text file
#
# Results: NDJSON records in evals/results/reviewer-<epoch>.ndjson; per-run
# transcript in evals/results/reviewer-<epoch>-run<i>.log and extracted
# findings text in the matching .findings.txt. Scoring reads only the
# findings text — a transcript echoes the spec under review, so every
# signature would match.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
FIXTURE_DIR="$FOUNDRY_REPO/evals/fixtures/reviewer"
TREE="$FIXTURE_DIR/tree"
ANSWER_KEY="$FIXTURE_DIR/answer-key.json"
AGENT_FILE="$FOUNDRY_REPO/plugins/foundry/agents/spec-reviewer.md"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

SCORE_ONLY=0
results=""

usage() { sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 2; }

emit() { # case verdict detail — append one NDJSON record (controlled, quote-free strings)
  local case_name="$1" verdict="$2" detail="$3"
  printf '{"event":"eval_case","fixture":"reviewer","case":"%s","verdict":"%s","detail":"%s"}\n' \
    "$case_name" "$verdict" "$detail" | tee -a "$results"
}

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

score_and_report() { # findings files... — score, print the summary line, propagate the verdict
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
  echo "reviewer-eval: $verdict mean_recall=$mean_recall decoys=$decoy_hits"
  return "$scorer_status"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --score-only) SCORE_ONLY=1; shift ;;
    -h|--help) usage ;;
    *) break ;;
  esac
done

mkdir -p "$RESULTS_DIR"
stamp="$(date +%s)"
results="$RESULTS_DIR/reviewer-$stamp.ndjson"

if [ "$SCORE_ONLY" -eq 1 ]; then
  if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then usage; fi
  echo "reviewer-eval: score-only findings=$1 results=$results"
  score_and_report "$1"
  exit
fi

[ "$#" -le 1 ] || usage
RUNS="${1:-3}"
case "$RUNS" in (*[!0-9]*|"") usage ;; esac
[ "$RUNS" -ge 1 ] || usage

echo "reviewer-eval: runs=$RUNS tree=$TREE"
echo "reviewer-eval: results=$results"

prompt="Read $AGENT_FILE and follow it exactly. Review roadmap/specs/widget-pricing/design.md. After the findings, output a footer block — one line per flagged item in the form: FLAGGED: <the exact offending term, identifier, or quoted phrase>. Include FLAGGED lines for flagged items only — anything noted as clean must NOT appear in a FLAGGED line."
findings_files=()
for ((run_number = 1; run_number <= RUNS; run_number++)); do
  log="$RESULTS_DIR/reviewer-$stamp-run$run_number.log"
  findings="$RESULTS_DIR/reviewer-$stamp-run$run_number.findings.txt"
  echo "reviewer-eval: run $run_number/$RUNS — headless review (this takes minutes), log=$log"
  if (cd "$TREE" && claude -p "$prompt" \
      --dangerously-skip-permissions \
      --verbose --output-format stream-json) >"$log" 2>&1; then
    emit "run$run_number:claude" "pass" "headless review completed"
  else
    emit "run$run_number:claude" "fail" "claude -p exited nonzero - see the log; empty findings score zero recall"
  fi
  extract_findings "$log" >"$findings"
  findings_files+=("$findings")
done

score_and_report "${findings_files[@]}"
