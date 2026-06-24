#!/usr/bin/env bash
# Recompute the final code-review footer + verdict from the reviewer's report and
# the cross-model refuter's KEEP/DROP verdicts.
#
# DROP-only: a `DROP <signature>` line removes the matching reviewer `FLAGGED:`
# line; anything else (KEEP, an absent signature) changes nothing — the refuter can
# never ADD a finding (recall-monotone-down, precision-up). Verdict: the FLAGGED
# footer lists blocking findings only, so the result is `CODE_REVIEW: FAIL` iff a
# FLAGGED line survives, else `CODE_REVIEW: PASS`. This is the step the wrapper
# previously faked with a hardcoded echo (CR-1).
#
# Usage: recompute-footer.sh <report-file> [refuter-output-file]
# Prints the surviving FLAGGED lines (order preserved) then the verdict line.
set -euo pipefail

report="${1:?usage: recompute-footer.sh <report-file> [refuter-output-file]}"
refuter="${2:-/dev/null}"

candidates="$(grep -E '^FLAGGED:' "$report" 2>/dev/null || true)"
drops="$(grep -E '^DROP[[:space:]]' "$refuter" 2>/dev/null | sed -E 's/^DROP[[:space:]]+//' || true)"

survivors=""
fail=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  sig="$(printf '%s' "$line" | sed -E 's/^FLAGGED:[[:space:]]*//')"
  dropped=0
  if [ -n "$drops" ]; then
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      if [ "$sig" = "$d" ]; then dropped=1; break; fi
    done <<< "$drops"
  fi
  if [ "$dropped" -eq 0 ]; then
    survivors+="$line"$'\n'
    fail=1
  fi
done <<< "$candidates"

printf '%s' "$survivors"
if [ "$fail" -eq 1 ]; then echo "CODE_REVIEW: FAIL"; else echo "CODE_REVIEW: PASS"; fi
