#!/usr/bin/env python3
"""Grade navigation-eval runs against an independent answer key.

Per (task, arm, run) transcript: did the ANSWER match the key (success), did it
rely on a decoy (decoy hit), what fraction of the gold spans were loaded into
context (context recall), how many tool calls, and what context cost (tokens,
USD). Emits one NDJSON eval_case per run, one summary per arm, and one fixture
summary. A non-discriminating fixture — no arm ever wrong and no decoy ever hit —
is reported as such and exits non-zero, never passed (AC-1.7).

Independence: this grader shares no code with any arm. It does NOT import
knowledge.py (the disclosure arm's tool); it re-implements heading scanning so the
oracle stays independent of the system under test. Pure stdlib.

Usage:
  grade_navigation.py <answer-key.json> <runs-manifest.json> --tree <dir> [--results <ndjson>]

runs-manifest.json: [{"task":"T1","arm":"full-load","run":1,"transcript":"<path>"}, ...]
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict

from eval_tokens import (
    final_text,
    iter_records,
    loaded_content_tokens,
    usage_from_transcript,
)

ANSWER_RE = re.compile(r"^answer:\s*(.*)$", re.IGNORECASE | re.MULTILINE)


def fail_usage(message):
    print(f"grade_navigation: {message}", file=sys.stderr)
    sys.exit(2)


def extract_answer(text):
    """The value on the last `ANSWER: <value>` line, or None if the protocol
    line is absent (an unscoreable run)."""
    found = ANSWER_RE.findall(text or "")
    return found[-1].strip() if found else None


def signature_matches(signature, text_lower):
    """Word-boundary, case-insensitive match, so a terse answer '5' counts but
    '15' does not."""
    return (
        re.search(r"\b" + re.escape(signature.lower()) + r"\b", text_lower) is not None
    )


def heading_line_ranges(text):
    """Map each ATX heading (lowercased) -> (start_line, end_line), 1-based,
    end exclusive at the next equal-or-higher heading. Independent re-implementation;
    deliberately does not import knowledge.py."""
    lines = text.splitlines()
    headings = []
    in_fence = False
    for lineno, line in enumerate(lines, start=1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,6})\s+(.*)", line)
        if match:
            headings.append(
                (len(match.group(1)), match.group(2).strip().lower(), lineno)
            )
    ranges = {}
    for index, (level, text_lower, start) in enumerate(headings):
        end = len(lines) + 1
        for next_level, _, next_start in headings[index + 1 :]:
            if next_level <= level:
                end = next_start
                break
        ranges.setdefault(text_lower, (start, end))
    return ranges


def tool_uses(records):
    """Yield each tool_use block across the assistant messages."""
    for record in records:
        if record.get("type") != "assistant":
            continue
        message = record.get("message", {})
        for block in message.get("content", []) if isinstance(message, dict) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block


def gold_covered(gold, records, tree_dir):
    """Did the agent load this gold span {file, heading} into context — by a Read
    overlapping its line range (or a full read of the file), or a `knowledge.py
    section` of its heading? Grep is a locator, not a load, so it does not count."""
    gold_file = gold["file"]
    gold_heading = gold["heading"].lower()
    gold_basename = os.path.basename(gold_file)

    gold_range = None
    abspath = os.path.join(tree_dir, gold_file)
    if os.path.exists(abspath):
        with open(abspath, encoding="utf-8", errors="replace") as handle:
            gold_range = heading_line_ranges(handle.read()).get(gold_heading)

    for block in tool_uses(records):
        name = block.get("name")
        params = block.get("input", {}) or {}
        if name == "Read":
            if os.path.basename(params.get("file_path", "")) != gold_basename:
                continue
            offset = params.get("offset")
            limit = params.get("limit")
            if offset is None and limit is None:
                return True  # full read of the gold file
            if gold_range is None:
                return True  # range unknown — a read of the file counts
            start = offset or 1
            end = start + (limit if limit is not None else 10**9)
            if start < gold_range[1] and end > gold_range[0]:
                return True  # read range overlaps the gold section
        elif name == "Bash":
            command = (params.get("command") or "").lower()
            heading_head = gold_heading.split()[0] if gold_heading else ""
            if (
                "knowledge.py section" in command
                and gold_basename.lower() in command
                and heading_head in command
            ):
                return True
    return False


def grade_transcript(transcript_path, task_key, tree_dir):
    """Score one run. Returns success, decoy_hit, context_recall, tool_calls,
    protocol_ok, and the token metrics."""
    records = list(iter_records(transcript_path))
    tokens = usage_from_transcript(transcript_path)
    tokens["loaded_content_tokens"] = loaded_content_tokens(transcript_path)
    tool_calls = sum(1 for _ in tool_uses(records))
    answer = extract_answer(final_text(transcript_path))

    if answer is None:
        return {
            "success": False,
            "decoy_hit": False,
            "context_recall": 0.0,
            "tool_calls": tool_calls,
            "protocol_ok": False,
            **tokens,
        }

    answer_lower = answer.lower()
    success = signature_matches(task_key["correct_signature"], answer_lower)
    decoy_hit = any(
        signature_matches(decoy["signature"], answer_lower)
        for decoy in task_key.get("decoys", [])
    )
    gold_spans = task_key.get("gold_spans", [])
    covered = sum(1 for gold in gold_spans if gold_covered(gold, records, tree_dir))
    recall = round(covered / len(gold_spans), 4) if gold_spans else 0.0
    return {
        "success": success,
        "decoy_hit": decoy_hit,
        "context_recall": recall,
        "tool_calls": tool_calls,
        "protocol_ok": True,
        **tokens,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answer_key")
    parser.add_argument("runs_manifest")
    parser.add_argument(
        "--tree", required=True, help="the fixture tree the runs executed in"
    )
    parser.add_argument("--results", help="also append NDJSON records here")
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        metavar="K=V",
        help="key=value added to every emitted record (e.g. corpus_size=50)",
    )
    args = parser.parse_args()

    with open(args.answer_key, encoding="utf-8") as handle:
        answer_key = json.load(handle)
    tasks_by_id = {task["id"]: task for task in answer_key.get("tasks", [])}
    if not tasks_by_id:
        fail_usage(f"{args.answer_key} lists no tasks")
    with open(args.runs_manifest, encoding="utf-8") as handle:
        runs = json.load(handle)

    fixture = answer_key.get("fixture", "navigation")
    results_handle = open(args.results, "a", encoding="utf-8") if args.results else None

    def parse_tag(raw):
        key, _, value = raw.partition("=")
        return key, int(value) if value.isdigit() else value

    tags = dict(parse_tag(raw) for raw in args.tag)

    def emit(record):
        line = json.dumps({**record, **tags})
        print(line)
        if results_handle:
            results_handle.write(line + "\n")

    per_arm = defaultdict(list)
    any_failure = False
    any_decoy = False
    for run in runs:
        task_id = run["task"]
        if task_id not in tasks_by_id:
            fail_usage(f"run references unknown task {task_id!r}")
        metrics = grade_transcript(run["transcript"], tasks_by_id[task_id], args.tree)
        verdict = (
            "pass"
            if (
                metrics["success"]
                and not metrics["decoy_hit"]
                and metrics["protocol_ok"]
            )
            else "fail"
        )
        if verdict == "fail":
            any_failure = True
        if metrics["decoy_hit"]:
            any_decoy = True
        per_arm[run["arm"]].append(metrics)
        emit(
            {
                "event": "eval_case",
                "fixture": fixture,
                "task": task_id,
                "arm": run["arm"],
                "run": run.get("run", 1),
                "verdict": verdict,
                "success": metrics["success"],
                "decoy_hit": metrics["decoy_hit"],
                "context_recall": metrics["context_recall"],
                "tool_calls": metrics["tool_calls"],
                "context_tokens": metrics["context_tokens"],
                "loaded_content_tokens": metrics["loaded_content_tokens"],
                "output_tokens": metrics["output_tokens"],
                "total_cost_usd": round(metrics["total_cost_usd"], 6),
                "protocol_ok": metrics["protocol_ok"],
            }
        )

    def mean(values):
        return round(sum(values) / len(values), 4) if values else 0.0

    for arm, runs_metrics in sorted(per_arm.items()):
        emit(
            {
                "event": "summary",
                "fixture": fixture,
                "arm": arm,
                "runs": len(runs_metrics),
                "mean_success": mean(
                    [1.0 if m["success"] else 0.0 for m in runs_metrics]
                ),
                "mean_recall": mean([m["context_recall"] for m in runs_metrics]),
                "mean_context_tokens": round(
                    mean([m["context_tokens"] for m in runs_metrics])
                ),
                "mean_loaded_content_tokens": round(
                    mean([m["loaded_content_tokens"] for m in runs_metrics])
                ),
                "mean_cost_usd": round(
                    mean([m["total_cost_usd"] for m in runs_metrics]), 6
                ),
                "decoy_hits": sum(1 for m in runs_metrics if m["decoy_hit"]),
            }
        )

    # A fixture that never trips any arm and never lures a decoy cannot tell the
    # arms apart — report it, do not pass it (AC-1.7).
    discriminating = any_failure or any_decoy
    emit(
        {
            "event": "summary",
            "fixture": fixture,
            "scope": "fixture",
            "discriminating": discriminating,
            "verdict": "ok" if discriminating else "non-discriminating",
        }
    )
    if results_handle:
        results_handle.close()
    if not discriminating:
        print(
            "grade_navigation: fixture is non-discriminating — no arm failed and no "
            "decoy was hit; the eval cannot compare arms",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
