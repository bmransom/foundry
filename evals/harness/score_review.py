"""Score spec-reviewer findings against a reviewer fixture's answer-key.json.

Usage: score_review.py <answer-key.json> <findings.txt> [<findings.txt> ...]
                       [--results <path>]

Each findings file is one run's findings text — the agent's final output, never
the raw transcript (a transcript echoes the spec under review, so every
signature would match). Emits one NDJSON eval_case record per violation and
per decoy per run, then one summary record:

    {"event": "eval_case", "fixture": "reviewer", "run": 1,
     "case": "violation:V1", "verdict": "pass|fail", "detail": ...}
    {"event": "summary", "fixture": "reviewer", "runs": N,
     "per_run_recall": [...], "mean_recall": ..., "min_recall": ...,
     "decoy_hits": ..., "verdict": "pass|fail"}

Detection proxy: a violation is DETECTED when its signature appears in the
findings text (case-insensitive substring); a decoy is HIT the same way.

Known v1 limitation: signature presence is the whole test. The agent "notes
clean files", so a decoy signature quoted in a clean-file note would count as
a hit; decoy signatures are therefore tokens the agent would only repeat when
flagging them. Calibrate against the first real runs (Task 7.2) before
trusting close calls.

Pass bar (provisional, calibrate in Task 7.2): mean recall >= 4/5 AND zero
decoy hits. Exits 1 on FAIL, 2 on bad input. Pure stdlib.
"""

import argparse
import json
import sys
from fractions import Fraction

RECALL_BAR = Fraction(4, 5)
MAX_DECOY_HITS = 0


def fail_usage(message):
    print(f"score_review: {message}", file=sys.stderr)
    sys.exit(2)


def read_findings(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError as error:
        fail_usage(f"cannot read findings file: {error}")


def signature_present(signature, findings_text):
    return signature.lower() in findings_text.lower()


def score_run(answer_key, run_number, findings_text):
    """Yield (case, verdict_ok, detail) per violation and decoy for one run."""
    for violation in answer_key["violations"]:
        signature = violation["signature"]
        detected = signature_present(signature, findings_text)
        detail = (
            f"signature {signature!r} present in findings ({violation['kind']})"
            if detected
            else f"signature {signature!r} absent from findings ({violation['kind']})"
        )
        yield f"violation:{violation['id']}", detected, detail
    for decoy in answer_key["decoys"]:
        signature = decoy["signature"]
        hit = signature_present(signature, findings_text)
        detail = (
            f"decoy signature {signature!r} present in findings - precision failure"
            if hit
            else f"decoy signature {signature!r} absent from findings"
        )
        yield f"decoy:{decoy['id']}", not hit, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answer_key", help="path to answer-key.json")
    parser.add_argument("findings", nargs="+", help="one findings text file per run")
    parser.add_argument("--results", help="also append NDJSON records to this path")
    args = parser.parse_args()

    with open(args.answer_key, encoding="utf-8") as handle:
        answer_key = json.load(handle)
    fixture = answer_key.get("fixture", "reviewer")
    violations = answer_key.get("violations") or []
    answer_key.setdefault("decoys", [])
    if not violations:
        fail_usage(f"{args.answer_key} lists no violations")
    findings_texts = [read_findings(path) for path in args.findings]

    results_handle = open(args.results, "a", encoding="utf-8") if args.results else None

    def emit(record):
        line = json.dumps(record)
        print(line)
        if results_handle:
            results_handle.write(line + "\n")

    per_run_recall = []
    decoy_hits = 0
    for run_number, findings_text in enumerate(findings_texts, start=1):
        detected_count = 0
        for case, verdict_ok, detail in score_run(
            answer_key, run_number, findings_text
        ):
            if case.startswith("violation:"):
                detected_count += 1 if verdict_ok else 0
            else:
                decoy_hits += 0 if verdict_ok else 1
            emit(
                {
                    "event": "eval_case",
                    "fixture": fixture,
                    "run": run_number,
                    "case": case,
                    "verdict": "pass" if verdict_ok else "fail",
                    "detail": detail,
                }
            )
        per_run_recall.append(Fraction(detected_count, len(violations)))

    mean_recall = sum(per_run_recall) / len(per_run_recall)
    min_recall = min(per_run_recall)
    passed = mean_recall >= RECALL_BAR and decoy_hits <= MAX_DECOY_HITS
    emit(
        {
            "event": "summary",
            "fixture": fixture,
            "runs": len(per_run_recall),
            "per_run_recall": [round(float(recall), 4) for recall in per_run_recall],
            "mean_recall": round(float(mean_recall), 4),
            "min_recall": round(float(min_recall), 4),
            "decoy_hits": decoy_hits,
            "verdict": "pass" if passed else "fail",
        }
    )
    if results_handle:
        results_handle.close()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
