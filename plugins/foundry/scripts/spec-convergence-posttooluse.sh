#!/usr/bin/env bash
# PostToolUse adapter for the spec-convergence loop.
#
# Wire as a PostToolUse hook on Write|Edit|MultiEdit. It reads the tool payload on
# stdin, and when the edited file is a spec file (roadmap/specs/<feature>/*.md) it
# runs the convergence hook on that feature's spec dir and surfaces FINDINGS/CAP to
# the agent (exit 2). It is FAIL-SAFE: a non-spec edit, malformed payload, or any
# infra trouble (no tmux, unavailable reviewer, verdict drift) exits 0 — it never
# blocks an edit, it only nudges the convergence loop when a review actually ran.
#
# WIRING CONVENTION: in Claude Code settings, ALSO scope this with the hook `if` field
# — the native path filter — so the harness skips non-spec edits before running this
# script, e.g. "if": "Edit(/roadmap/specs/**/*.md)|Write(/roadmap/specs/**/*.md)|
# MultiEdit(/roadmap/specs/**/*.md)" (matcher still matches tool names only). The
# in-script path filter below stays regardless: it is the harness-agnostic guarantee
# (Codex has no `if`) and keeps the adapter correct if wired without `if`. A future
# code-review-posttooluse.sh mirrors this both-layers pattern.
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
