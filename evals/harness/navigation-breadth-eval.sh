#!/usr/bin/env bash
# Navigation breadth eval (Layer 3): sweep corpus size; for each size run every
# arm over the discovery task headless, grade against the independent answer key,
# and tag each record with corpus_size — so the cost-vs-corpus-size crossover
# (where structure-aware navigation overtakes grep) is visible.
#
# Usage:
#   evals/harness/navigation-breadth-eval.sh [N] [sizes...]   (default N=1, sizes "5 25 100")
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HARNESS/../.." && pwd)"
FIXTURE="$REPO/evals/fixtures/navigation-breadth"
TREE="$FIXTURE/tree"
RESULTS_DIR="$REPO/evals/results"
mkdir -p "$RESULTS_DIR"
stamp="$(date +%s)"
results="$RESULTS_DIR/navigation-breadth-$stamp.ndjson"

N="${1:-1}"; [ "$#" -gt 0 ] && shift || true
SIZES=("$@"); [ "${#SIZES[@]}" -gt 0 ] || SIZES=(5 25 100)

echo "navigation-breadth: N=$N sizes=${SIZES[*]} results=$results"
for size in "${SIZES[@]}"; do
  echo "navigation-breadth: building corpus size=$size"
  python3 "$FIXTURE/build_corpus.py" --count "$size" >/dev/null
  manifest="$RESULTS_DIR/navigation-breadth-$stamp-size$size-manifest.json"
  python3 - "$FIXTURE/tasks.json" "$N" "$RESULTS_DIR" "$stamp" "$size" "$manifest" "$TREE" <<'PY'
import json, os, subprocess, sys
tasks_path, n, results_dir, stamp, size, manifest_path, tree = sys.argv[1:8]
n = int(n)
config = json.load(open(tasks_path, encoding="utf-8"))
protocol = config["answer_protocol"]
entries = []
for task in config["tasks"]:
    for arm in config["arms"]:
        for run_number in range(1, n + 1):
            log = os.path.join(results_dir, f"navigation-breadth-{stamp}-size{size}-{task['id']}-{arm['id']}-run{run_number}.log")
            prompt = f"{arm['preamble']}\n\nQuestion: {task['question']}\n\n{protocol}"
            print(f"navigation-breadth: size={size} {task['id']}/{arm['id']}/run{run_number} (headless)", flush=True)
            with open(log, "w", encoding="utf-8") as out, open(os.devnull) as devnull:
                subprocess.run(
                    ["claude", "-p", prompt, "--output-format", "stream-json",
                     "--verbose", "--dangerously-skip-permissions"],
                    cwd=tree, stdin=devnull, stdout=out, stderr=subprocess.STDOUT, check=False,
                )
            entries.append({"task": task["id"], "arm": arm["id"], "run": run_number, "transcript": log})
with open(manifest_path, "w", encoding="utf-8") as handle:
    json.dump(entries, handle, indent=2)
PY
  python3 "$HARNESS/grade_navigation.py" "$FIXTURE/answer-key.json" "$manifest" \
    --tree "$TREE" --results "$results" --tag "corpus_size=$size" >/dev/null 2>&1 || true
done
echo "navigation-breadth: done -> $results"
