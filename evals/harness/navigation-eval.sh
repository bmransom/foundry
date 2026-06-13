#!/usr/bin/env bash
# Navigation eval (Layer 3): run each task under each arm N times via headless
# claude, then grade the transcripts against the independent answer key — context
# recall, decoy hits, and context cost (tokens) per arm. Honest framing: at
# affordable N this is a smoke alarm for large differences, not statistics.
#
# Usage:
#   evals/harness/navigation-eval.sh [N]                   (default N=3 runs)
#   evals/harness/navigation-eval.sh --grade-only <manifest.json>
#
# --grade-only  skip the headless claude calls; grade an existing runs manifest
#
# Results: NDJSON in evals/results/navigation-<epoch>.ndjson; per-run transcripts
# alongside; the runs manifest in evals/results/navigation-<epoch>-manifest.json.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
FIXTURE_DIR="$FOUNDRY_REPO/evals/fixtures/navigation"
TREE="$FIXTURE_DIR/tree"
ANSWER_KEY="$FIXTURE_DIR/answer-key.json"
TASKS="$FIXTURE_DIR/tasks.json"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

usage() { sed -n '2,15p' "${BASH_SOURCE[0]}"; exit 2; }

GRADE_ONLY=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --grade-only) GRADE_ONLY=1; shift ;;
    -h|--help) usage ;;
    *) break ;;
  esac
done

mkdir -p "$RESULTS_DIR"
stamp="$(date +%s)"
results="$RESULTS_DIR/navigation-$stamp.ndjson"

echo "navigation-eval: building fixture tree"
python3 "$FIXTURE_DIR/build_tree.py"

if [ "$GRADE_ONLY" -eq 1 ]; then
  [ "$#" -eq 1 ] && [ -f "$1" ] || usage
  echo "navigation-eval: grade-only manifest=$1 results=$results"
  python3 "$HARNESS/grade_navigation.py" "$ANSWER_KEY" "$1" --tree "$TREE" --results "$results"
  exit
fi

[ "$#" -le 1 ] || usage
RUNS="${1:-3}"
case "$RUNS" in (*[!0-9]*|"") usage ;; esac
[ "$RUNS" -ge 1 ] || usage

manifest="$RESULTS_DIR/navigation-$stamp-manifest.json"
echo "navigation-eval: runs=$RUNS results=$results"

# task × arm × run: headless claude in the tree; stdin from /dev/null to skip the
# "no stdin received" wait. The arm preamble is the only thing that varies.
python3 - "$TASKS" "$RUNS" "$RESULTS_DIR" "$stamp" "$manifest" "$TREE" <<'PY'
import json, os, subprocess, sys

tasks_path, runs, results_dir, stamp, manifest_path, tree = sys.argv[1:7]
runs = int(runs)
config = json.load(open(tasks_path, encoding="utf-8"))
protocol = config["answer_protocol"]

entries = []
for task in config["tasks"]:
    for arm in config["arms"]:
        for run_number in range(1, runs + 1):
            log = os.path.join(results_dir, f"navigation-{stamp}-{task['id']}-{arm['id']}-run{run_number}.log")
            prompt = f"{arm['preamble']}\n\nQuestion: {task['question']}\n\n{protocol}"
            print(f"navigation-eval: {task['id']} / {arm['id']} / run {run_number} (headless; minutes)", flush=True)
            with open(log, "w", encoding="utf-8") as out, open(os.devnull) as devnull:
                subprocess.run(
                    ["claude", "-p", prompt, "--output-format", "stream-json",
                     "--verbose", "--dangerously-skip-permissions"],
                    cwd=tree, stdin=devnull, stdout=out, stderr=subprocess.STDOUT, check=False,
                )
            entries.append({"task": task["id"], "arm": arm["id"], "run": run_number, "transcript": log})

with open(manifest_path, "w", encoding="utf-8") as handle:
    json.dump(entries, handle, indent=2)
print(f"navigation-eval: manifest -> {manifest_path}")
PY

echo "navigation-eval: grading"
python3 "$HARNESS/grade_navigation.py" "$ANSWER_KEY" "$manifest" --tree "$TREE" --results "$results"
