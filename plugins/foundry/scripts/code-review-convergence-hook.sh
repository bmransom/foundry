#!/usr/bin/env bash
# Code-review convergence loop control — the OUTER fix loop (mirrors
# spec-convergence-hook.sh).
#
# Each invocation runs one converged code review and turns the fix -> re-review
# cycle into a bounded loop:
#   - PASS verdict -> converged; Review clears, Finish may proceed (exit 0)
#   - FAIL verdict -> surface the FLAGGED items so the lifecycle agent fixes via
#                     the SDLC, which re-invokes this hook (the next round) (exit 2)
#   - cap reached  -> stop and escalate to the maintainer (exit 4)
#
# Termination is the deterministic `CODE_REVIEW: PASS` verdict, not prose. The
# per-spec round counter caps non-convergence (reviewer nondeterminism or an
# unsatisfiable finding) so the loop can't run forever. The reviewer is read-only
# and never fixes; the agent fixes between rounds.
set -euo pipefail

spec_dir="${1:?usage: code-review-convergence-hook.sh <spec-dir>}"
cap="${CODE_REVIEW_CONVERGENCE_CAP:-20}"
state_dir="${CODE_REVIEW_CONVERGENCE_STATE:-.foundry/tmp/code-review-convergence}"
plugin_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
review_cmd="${CODE_REVIEW_REVIEW_CMD:-$plugin_root/skills/code-review/scripts/spawn-code-reviewer.sh}"

slug="$(printf '%s' "$spec_dir" | tr '/ ' '__')"
counter_file="$state_dir/$slug.round"
mkdir -p "$state_dir"
round="$(cat "$counter_file" 2>/dev/null || echo 0)"

if ! report="$("$review_cmd" "$spec_dir")"; then
  echo "code-review-convergence: ERROR — the review command failed or timed out; not converged" >&2
  exit 3
fi
verdict="$(printf '%s\n' "$report" | grep -E '^CODE_REVIEW: (PASS|FAIL)$' | tail -1 || true)"
[ -n "$verdict" ] || {
  echo "code-review-convergence: ERROR — no 'CODE_REVIEW: PASS|FAIL' verdict line (reviewer drift)" >&2
  exit 3
}

if [ "$verdict" = "CODE_REVIEW: PASS" ]; then
  echo 0 > "$counter_file"
  echo "code-review-convergence: PASS — converged (no blocking finding; Review clears)"
  exit 0
fi

round=$((round + 1))
printf '%s\n' "$round" > "$counter_file"
flagged="$(printf '%s\n' "$report" | grep -E '^FLAGGED:' || true)"

if [ "$round" -ge "$cap" ]; then
  echo 0 > "$counter_file"
  echo "code-review-convergence: CAP REACHED ($round/$cap) — escalate to the maintainer; do NOT auto-pass. Remaining:"
  printf '%s\n' "$flagged"
  exit 4
fi

echo "code-review-convergence: FINDINGS (round $round/$cap) — fix via the SDLC and re-review:"
printf '%s\n' "$flagged"
exit 2
