#!/usr/bin/env python3
"""Grade a triggering-eval run against the independent case oracle.

Per case: the runner produced one or more predictions (which skill a fresh model
would route the query to, or NONE). A case PASSES when the share of predictions
matching the oracle `expect` meets --min-rate. Emits one NDJSON eval_case per
case, one summary per category, and a fixture summary with overall accuracy and
the top confusion pairs (expect -> predicted) so a regression names itself.

Independence: this grader shares no code with the skills under test and never
reads their descriptions. The oracle is the human-authored `expect` label in
cases.json; the grader only compares strings. Pure stdlib.

A non-discriminating corpus — one lacking either a should-trigger case
(expect != NONE) or a should-not-trigger case (expect == NONE) — cannot tell a
real router from "always NONE" or "always skill X", so it exits non-zero rather
than reporting a hollow pass.

Usage:
  grade_triggering.py <cases.json> <predictions.json> [--results <ndjson>] [--min-rate 0.5]

predictions.json: [{"id": "perf-latency", "predicted": "performance"}, ...]
  One entry per run; repeat an id to record multiple runs of the same case.
"""

import argparse
import json
import sys
from collections import defaultdict


def fail_usage(message):
    print(f"grade_triggering: {message}", file=sys.stderr)
    sys.exit(2)


def norm(label):
    return (label or "").strip().lower()


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("cases")
    parser.add_argument("predictions")
    parser.add_argument("--results", default=None)
    parser.add_argument("--min-rate", type=float, default=0.5)
    args = parser.parse_args()

    try:
        with open(args.cases, encoding="utf-8") as handle:
            cases = json.load(handle).get("cases", [])
    except (OSError, json.JSONDecodeError) as err:
        fail_usage(f"cannot read cases: {err}")
    try:
        with open(args.predictions, encoding="utf-8") as handle:
            predictions = json.load(handle)
    except (OSError, json.JSONDecodeError) as err:
        fail_usage(f"cannot read predictions: {err}")

    if not cases:
        fail_usage("no cases in fixture")
    expects = {norm(c.get("expect")) for c in cases}
    if "none" not in expects or expects <= {"none"}:
        fail_usage(
            "non-discriminating corpus: need both should-trigger and should-not-trigger cases"
        )

    preds_by_id = defaultdict(list)
    for entry in predictions:
        preds_by_id[entry["id"]].append(norm(entry.get("predicted")))

    out = open(args.results, "w", encoding="utf-8") if args.results else None

    def emit(record):
        line = json.dumps(record)
        if out:
            out.write(line + "\n")
        else:
            print(line)

    by_category = defaultdict(lambda: {"cases": 0, "passed": 0})
    confusion = defaultdict(int)
    total_passed = 0

    for case in cases:
        case_id = case["id"]
        expect = norm(case.get("expect"))
        category = case.get("category", "uncategorized")
        runs = preds_by_id.get(case_id)
        if not runs:
            fail_usage(f"no predictions for case {case_id} (unscoreable run)")
        hits = sum(1 for p in runs if p == expect)
        rate = hits / len(runs)
        verdict = "pass" if rate >= args.min_rate else "fail"
        for predicted in runs:
            if predicted != expect:
                confusion[f"{expect or 'NONE'}->{predicted or 'NONE'}"] += 1
        by_category[category]["cases"] += 1
        if verdict == "pass":
            by_category[category]["passed"] += 1
            total_passed += 1
        emit(
            {
                "event": "eval_case",
                "fixture": "triggering",
                "id": case_id,
                "category": category,
                "expect": case.get("expect"),
                "runs": len(runs),
                "hits": hits,
                "rate": round(rate, 3),
                "verdict": verdict,
            }
        )

    for category in sorted(by_category):
        stats = by_category[category]
        emit(
            {
                "event": "category_summary",
                "category": category,
                "cases": stats["cases"],
                "passed": stats["passed"],
            }
        )

    top_confusion = sorted(confusion.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    emit(
        {
            "event": "fixture_summary",
            "fixture": "triggering",
            "cases": len(cases),
            "passed": total_passed,
            "accuracy": round(total_passed / len(cases), 3),
            "discriminating": True,
            "top_confusion": [
                {"pair": pair, "count": count} for pair, count in top_confusion
            ],
        }
    )

    if out:
        out.close()

    sys.exit(0 if total_passed == len(cases) else 1)


if __name__ == "__main__":
    main()
