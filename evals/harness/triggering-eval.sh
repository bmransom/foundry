#!/usr/bin/env bash
# Triggering eval (Layer 3): for each case, ask a fresh headless `claude -p` which
# single foundry skill should handle the message — given the LIVE descriptions
# read from each SKILL.md — then grade predictions against the independent oracle
# in cases.json. Honest framing: this measures whether the current descriptions
# route correctly (a proxy for live triggering); at affordable N it is a smoke
# alarm for description regressions, not statistics.
#
# Usage:
#   triggering-eval.sh [N]                        run N times per case (default 1)
#   triggering-eval.sh --harness claude|codex     which headless harness classifies (default claude)
#   triggering-eval.sh --dry-run                  print the prompt for one case; spawn nothing
#   triggering-eval.sh --grade-only <preds.json>  grade an existing predictions file
#
# Results: predictions + NDJSON verdicts in evals/results/triggering-<epoch>.*
set -euo pipefail
HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
SKILLS_DIR="$FOUNDRY_REPO/plugins/foundry/skills"
CASES="$FOUNDRY_REPO/evals/fixtures/triggering/cases.json"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"
GRADER="$HARNESS/grade_triggering.py"

usage() { sed -n '2,15p' "${BASH_SOURCE[0]}"; exit 2; }

MODE=run
GRADE_FILE=""
CLASSIFY_REPLY=""
HARNESS_CLI=claude
RUNS=1
while [ "$#" -gt 0 ]; do
  case "$1" in
    --dry-run) MODE=dry; shift ;;
    --grade-only) MODE=grade; shift; GRADE_FILE="${1:-}"; [ "$#" -gt 0 ] && shift || true ;;
    --classify-reply) MODE=classify; shift; CLASSIFY_REPLY="${1:-}"; [ "$#" -gt 0 ] && shift || true ;;
    --harness) shift; HARNESS_CLI="${1:-claude}"; [ "$#" -gt 0 ] && shift || true ;;
    -h|--help) usage ;;
    *) RUNS="$1"; shift ;;
  esac
done
case "$HARNESS_CLI" in claude|codex) ;; *) echo "triggering-eval: unknown harness '$HARNESS_CLI' (claude|codex)" >&2; exit 2 ;; esac

if [ "$MODE" = grade ]; then
  [ -n "$GRADE_FILE" ] && [ -f "$GRADE_FILE" ] || usage
  python3 "$GRADER" "$CASES" "$GRADE_FILE"
  exit
fi

python3 - "$SKILLS_DIR" "$CASES" "$RESULTS_DIR" "$RUNS" "$MODE" "$GRADER" "$CLASSIFY_REPLY" "$HARNESS_CLI" <<'PY'
import json, os, re, subprocess, sys, time

skills_dir, cases_path, results_dir, runs, mode, grader = sys.argv[1:7]
classify_reply = sys.argv[7] if len(sys.argv) > 7 else ""
harness_cli = sys.argv[8] if len(sys.argv) > 8 else "claude"
runs = int(runs)


def description(skill_md):
    """The frontmatter description, joining YAML continuation lines."""
    lines, capturing, in_fm = [], False, False
    with open(skill_md, encoding="utf-8") as handle:
        for index, raw in enumerate(handle):
            text = raw.rstrip("\n")
            if index == 0:
                if text.strip() == "---":
                    in_fm = True
                    continue
                break
            if in_fm and text.strip() == "---":
                break
            if not in_fm:
                continue
            if text.startswith("description:"):
                lines = [text[len("description:"):].strip()]
                capturing = True
            elif capturing and (text.startswith(" ") or text.startswith("\t")):
                lines.append(text.strip())
            elif capturing:
                capturing = False
    return " ".join(lines).strip().strip('"')


skills = []
for name in sorted(os.listdir(skills_dir)):
    md = os.path.join(skills_dir, name, "SKILL.md")
    if os.path.isfile(md):
        desc = description(md)
        if desc:
            skills.append((name, desc))

catalog = "\n".join(f"- {name}: {desc}" for name, desc in skills)
names = [name for name, _ in skills]


def match_reply(first):
    """Map a model's first reply line to a skill name, or NONE. Try the LONGEST
    name first: a name that is a prefix of another (code vs code-review) would
    otherwise steal a correct longer answer, because the hyphen is a word boundary
    and `\\bcode\\b` matches inside `code-review`."""
    first = first.strip().lower()
    for name in sorted(names, key=len, reverse=True):
        if re.search(r"\b" + re.escape(name.lower()) + r"\b", first):
            return name
    return "NONE"


def build_prompt(query):
    return (
        "Simulate Claude Code's skill-selection. Given the foundry skill catalog, "
        "pick the SINGLE skill that should handle the message, or NONE (the task is "
        "trivial, belongs to a non-foundry skill, or is unrelated). Answer with ONLY "
        "the skill name or NONE.\n\n"
        f"## Catalog\n{catalog}\n\n## Message\n{query}\n\n## Answer\n"
    )


cases = json.load(open(cases_path, encoding="utf-8"))["cases"]

if mode == "dry":
    print(f"skills: {len(skills)} | cases: {len(cases)}")
    print("--- prompt for first case ---")
    print(build_prompt(cases[0]["query"]))
    sys.exit(0)

if mode == "classify":
    # Hermetic: exercise the reply->skill matcher on a fixed reply, no model spawn.
    print(match_reply(classify_reply))
    sys.exit(0)


def _codex_reply(stdout):
    """The last agent_message text in codex exec's --json JSONL stream (its final reply)."""
    text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed" and event.get("item", {}).get("type") == "agent_message":
            text = event["item"].get("text") or text
    return text


def classify(query):
    prompt = build_prompt(query)
    if harness_cli == "codex":
        # codex reads the prompt on stdin ("-"); read-only sandbox — this only classifies.
        result = subprocess.run(
            ["codex", "exec", "--json", "--sandbox", "read-only", "-"],
            input=prompt, capture_output=True, text=True, timeout=300,
        )
        reply = _codex_reply(result.stdout or "")
    else:
        result = subprocess.run(
            ["claude", "-p", prompt], capture_output=True, text=True, timeout=180
        )
        reply = (result.stdout or "").strip()
    lines = [line for line in reply.splitlines() if line.strip()]
    return match_reply(lines[0] if lines else "")


os.makedirs(results_dir, exist_ok=True)
stamp = str(int(time.time()))
predictions = []
for case in cases:
    for _ in range(runs):
        predictions.append({"id": case["id"], "predicted": classify(case["query"])})

preds_path = os.path.join(results_dir, f"triggering-{stamp}-preds.json")
with open(preds_path, "w", encoding="utf-8") as handle:
    json.dump(predictions, handle, indent=2)
results = os.path.join(results_dir, f"triggering-{stamp}.ndjson")
code = subprocess.run(["python3", grader, cases_path, preds_path, "--results", results]).returncode
print(f"triggering-eval: predictions={preds_path} results={results}")
sys.exit(code)
PY
