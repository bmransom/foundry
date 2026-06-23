#!/usr/bin/env bash
# PostToolUse adapter for the spec-convergence loop.
#
# Wire as a PostToolUse hook on Write|Edit|MultiEdit. It reads the tool payload on
# stdin, and when the edited file is a spec file (roadmap/specs/<feature>/*.md) it
# runs the convergence hook on that feature's spec dir and surfaces FINDINGS/CAP to
# the agent (exit 2). It is FAIL-SAFE: a non-spec edit, malformed payload, or any
# infra trouble (no tmux, unavailable reviewer, verdict drift) exits 0 — it never
# blocks an edit, it only nudges the convergence loop when a review actually ran.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
payload="$(cat || true)"

file="$(printf '%s' "$payload" | python3 -c '
import sys, json
try:
    data = json.load(sys.stdin)
except Exception:
    print(""); sys.exit(0)
print((data.get("tool_input") or {}).get("file_path", "") or "")
' 2>/dev/null || true)"

case "$file" in
  *roadmap/specs/*/*.md) ;;
  *) exit 0 ;;  # not a spec file — no-op
esac

spec_dir="$(dirname "$file")"

set +e
out="$("$here/spec-convergence-hook.sh" "$spec_dir" 2>&1)"
rc=$?
set -e

case "$rc" in
  2|4) printf '%s\n' "$out" >&2; exit 2 ;;  # FINDINGS or CAP -> surface to the agent
  *) exit 0 ;;                               # CLEAN / drift / infra -> never block
esac
