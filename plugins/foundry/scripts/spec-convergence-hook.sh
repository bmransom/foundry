#!/usr/bin/env bash
# Spec-convergence loop control (the forcing function for spec-review).
#
# Wired as a PostToolUse hook on edits to spec files, this runs spec-review and
# turns the natural edit -> review -> edit cycle into a bounded convergence loop:
#   - CLEAN verdict   -> converged; nothing to fix, the loop ends on its own
#   - FINDINGS verdict -> surface the FLAGGED items so the agent edits, which
#                         re-fires this hook (the next round)
#   - cap reached     -> stop firing and escalate to the human (hold the gate)
#
# Termination is the deterministic `SPEC_REVIEW: CLEAN` verdict, not prose. The
# per-spec round counter caps non-convergence (reviewer nondeterminism / an
# unsatisfiable finding) so the loop can't run forever.
#
# spec-review must emit, as its last line, `SPEC_REVIEW: CLEAN` or
# `SPEC_REVIEW: FINDINGS` (plus `FLAGGED:` lines) — that contract is the other
# half of this feature.
set -euo pipefail

spec_dir="${1:?usage: spec-convergence-hook.sh <spec-dir>}"
cap="${SPEC_CONVERGENCE_CAP:-10}"
state_dir="${SPEC_CONVERGENCE_STATE:-.foundry/tmp/spec-convergence}"
plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
review_cmd="${SPEC_CONVERGENCE_REVIEW_CMD:-$plugin_root/skills/spec-review/scripts/spawn-spec-reviewer.sh}"

slug="$(printf '%s' "$spec_dir" | tr '/ ' '__')"
counter_file="$state_dir/$slug.round"
mkdir -p "$state_dir"
round="$(cat "$counter_file" 2>/dev/null || echo 0)"

report="$("$review_cmd" "$spec_dir")"
verdict="$(printf '%s\n' "$report" | grep -E '^SPEC_REVIEW: (CLEAN|FINDINGS)$' | tail -1 || true)"
[ -n "$verdict" ] || {
  echo "spec-convergence: ERROR — no 'SPEC_REVIEW: CLEAN|FINDINGS' verdict line (spec-review drift)" >&2
  exit 3
}

if [ "$verdict" = "SPEC_REVIEW: CLEAN" ]; then
  echo 0 > "$counter_file"
  echo "spec-convergence: CLEAN — converged (no blocking findings remain; advisory prose may persist; present for Design approval)"
  exit 0
fi

round=$((round + 1))
printf '%s\n' "$round" > "$counter_file"
flagged="$(printf '%s\n' "$report" | grep -E '^FLAGGED:' || true)"

if [ "$round" -ge "$cap" ]; then
  echo 0 > "$counter_file"
  echo "spec-convergence: CAP REACHED ($round/$cap) — escalate to the human; do NOT auto-approve. Remaining:"
  printf '%s\n' "$flagged"
  exit 4
fi

echo "spec-convergence: FINDINGS (round $round/$cap) — apply these and re-edit:"
printf '%s\n' "$flagged"
exit 2
