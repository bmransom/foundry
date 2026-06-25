#!/usr/bin/env bash
# Block until a code-review report is COMPLETE, then succeed so the caller can read it.
#
# The shared fresh-session runner spawns DETACHED, so the orchestrator can't wait on
# the reviewer process — it waits on the artifact. "Complete" = the report file exists
# AND ends with a `CODE_REVIEW: PASS|FAIL` verdict line; the output contract puts the
# verdict last, so its presence means the reviewer finished writing. Times out cleanly
# so a hung or never-spawned reviewer can't block forever. This is the synchronous
# foundation the runner needs (CR-1/CR-17) — proven by the T30 tracer bullet.
#
# Usage: wait-for-report.sh <report-path> [timeout-seconds] [poll-seconds]
# Exit: 0 when the report is complete; 1 on timeout (caller decides how to escalate).
set -euo pipefail

report="${1:?usage: wait-for-report.sh <report-path> [timeout-seconds] [poll-seconds]}"
timeout="${2:-300}"
poll="${3:-1}"

elapsed=0
while :; do
  if [ -f "$report" ] && grep -qE '^CODE_REVIEW: (PASS|FAIL)$' "$report"; then
    exit 0
  fi
  if awk "BEGIN{exit !($elapsed >= $timeout)}"; then
    echo "wait-for-report: TIMEOUT after ${timeout}s — no complete report at $report" >&2
    exit 1
  fi
  sleep "$poll"
  elapsed="$(awk "BEGIN{print $elapsed + $poll}")"
done
