#!/usr/bin/env bash
# Tracer bullet (T30): the synchronous spawn -> wait -> read foundation. The shared
# runner spawns DETACHED, so the orchestrator can't wait on the process — it waits on
# the report ARTIFACT (file exists AND ends with a CODE_REVIEW verdict line, which the
# output contract puts last). Proves: a ready report succeeds; a report that completes
# LATER blocks-then-succeeds; a verdict-less (still-writing) or absent report times out
# cleanly so a hung/never-spawned reviewer can't block forever. Hermetic — no tmux/claude.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
W="$REPO/plugins/foundry/skills/code-review/scripts/wait-for-report.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$W" ] || fail "missing/!executable wait-for-report.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# 1. A complete report already present -> succeed (first poll).
printf 'findings\nCODE_REVIEW: PASS\n' > "$work/ready"
"$W" "$work/ready" 5 0.1 || fail "1: a ready report should succeed"

# 2. Report completes LATER -> block until the verdict line appears, then succeed.
( sleep 0.3; printf 'findings\nFLAGGED: x\nCODE_REVIEW: FAIL\n' > "$work/late" ) &
"$W" "$work/late" 5 0.1 || fail "2: should block until the report completes"
grep -qx "CODE_REVIEW: FAIL" "$work/late" || fail "2: report should be readable after the wait"
wait

# 3. Report exists but has NO verdict line (still writing) -> time out (verdict-gated).
printf 'findings only, still writing...\n' > "$work/partial"
if "$W" "$work/partial" 1 0.1 2>/dev/null; then fail "3: an incomplete report must time out, not succeed"; fi

# 4. No report at all -> time out cleanly (never-spawned reviewer).
if "$W" "$work/missing" 1 0.1 2>/dev/null; then fail "4: a missing report must time out"; fi

echo "wait_for_report_test: PASS"
