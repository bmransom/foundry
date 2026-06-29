#!/usr/bin/env python3
"""Grade a debug-eval run: did the agent *localize the fault with the debugger*?

Reads the fixture answer-key and a transcript of the agent's session, and scores
four signals from the transcript text:

  debugger_used  — an lldb/gdb session actually ran (a prompt, a stop reason)
  breakpoint_hit — execution stopped at a breakpoint, watchpoint, or the fault
  inspected      — state was read (frame variable / print / backtrace / registers)
  localized      — the faulting file:line, function, or a known phrasing is named

A run PASSES only when all four hold. This is the discrimination the eval buys: a
*static* run that reads the source and guesses the right line still FAILS, because
it leaves no debugger-used / breakpoint-hit / inspected evidence. The grader shares
no code with the skill and judges only the transcript against the human answer-key.

Usage:
  grade_debug.py <answer-key.json> <transcript> [--results <ndjson>]
"""

import argparse
import json
import re
import sys

# Evidence patterns (matched case-insensitively against the transcript).
DEBUGGER_USED = [
    r"\(lldb\)", r"\(gdb\)", r"lldb\s+--?batch", r"lldb\s+-[a-z]", r"gdb\s+--batch",
    r"stop reason\s*=", r"\bbr(?:eakpoint)?\s+set\b", r"\bbreak\s+\w+\.c:",
]
BREAKPOINT_HIT = [
    r"stop reason\s*=\s*breakpoint", r"process\s+\d+\s+stopped",
    r"thread\s+#?\d+.*stopped", r"breakpoint\s+\d+(?:\.\d+)?,", r"hit breakpoint",
    r"stop reason\s*=\s*watchpoint", r"exc_bad_access", r"sigsegv", r"sigabrt",
    r"heap-buffer-overflow",
]
INSPECTED = [
    r"\bframe\s+variable\b", r"\binfo\s+(?:locals|args)\b", r"\(lldb\)\s*p\b",
    r"\(gdb\)\s*p\b", r"\bbacktrace\b", r"\bbt\b", r"frame\s+#\d+",
    r"\bregister\s+read\b", r"\binfo\s+registers\b", r"\(\s*int\s*\)\s*\w+\s*=",
]


def fail_usage(message):
    print(f"grade_debug: {message}", file=sys.stderr)
    sys.exit(2)


def any_match(patterns, text):
    return any(re.search(p, text) for p in patterns)


def localized(answer, text):
    fname = answer.get("file", "")
    for line in answer.get("fault_lines", []):
        if f"{fname}:{line}".lower() in text or f"line {line}" in text:
            return True
    for token in answer.get("localize_any", []):
        if token.lower() in text:
            return True
    return False


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("answer_key")
    parser.add_argument("transcript")
    parser.add_argument("--results", default=None)
    args = parser.parse_args()

    try:
        with open(args.answer_key, encoding="utf-8") as handle:
            answer = json.load(handle)
    except (OSError, json.JSONDecodeError) as err:
        fail_usage(f"cannot read answer-key: {err}")
    try:
        with open(args.transcript, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError as err:
        fail_usage(f"cannot read transcript: {err}")

    if not answer.get("localize_any") and not answer.get("fault_lines"):
        fail_usage("answer-key has no fault_lines or localize_any to localize against")

    text = raw.lower()
    signals = {
        "debugger_used": any_match(DEBUGGER_USED, text),
        "breakpoint_hit": any_match(BREAKPOINT_HIT, text),
        "inspected": any_match(INSPECTED, text),
        "localized": localized(answer, text),
    }
    passed = all(signals.values())

    out = open(args.results, "w", encoding="utf-8") if args.results else None

    def emit(record):
        line = json.dumps(record)
        out.write(line + "\n") if out else print(line)

    emit({
        "event": "eval_case",
        "fixture": "debug",
        "bug": answer.get("bug"),
        "signals": signals,
        "verdict": "pass" if passed else "fail",
        "missing": [k for k, v in signals.items() if not v],
    })
    emit({
        "event": "fixture_summary",
        "fixture": "debug",
        "verdict": "pass" if passed else "fail",
    })

    if out:
        out.close()
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
