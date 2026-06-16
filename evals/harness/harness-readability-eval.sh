#!/usr/bin/env bash
# Harness-readability eval (AC-5.3, AC-5.6): asserts a repo carries the harness-agnostic
# layout for its declared harness set. Harness-owned grading — shares no code with the
# bootstrap/update skills, so a skill never grades itself.
# Usage: harness-readability-eval.sh <repo> <harness>...   (e.g. ... /path claude-code codex)
set -euo pipefail
REPO="${1:?usage: harness-readability-eval.sh <repo> <harness>...}"; shift
HARNESSES=("$@"); [ "${#HARNESSES[@]}" -gt 0 ] || { echo "no harness set given" >&2; exit 2; }

fail=0
bad() { echo "readability: FAIL — $1"; fail=1; }
has() { local h; for h in "${HARNESSES[@]}"; do [ "$h" = "$1" ] && return 0; done; return 1; }

# AGENTS.md — the shared instruction source, present for every harness.
[ -f "$REPO/AGENTS.md" ] || bad "AGENTS.md missing (the shared instruction source)"

# CLAUDE.md — present iff Claude Code is a target, and a pointer to AGENTS.md (not a copy).
if has claude-code; then
  if [ -e "$REPO/CLAUDE.md" ]; then
    [ -L "$REPO/CLAUDE.md" ] || bad "CLAUDE.md is a copy, not a symlink pointer to AGENTS.md"
  else
    bad "CLAUDE.md missing though claude-code is a target"
  fi
elif [ -e "$REPO/CLAUDE.md" ]; then
  bad "CLAUDE.md present though claude-code is not a target"
fi

# Rules at the neutral location, never .claude/rules/.
if [ -d "$REPO/.claude/rules" ]; then bad ".claude/rules/ present — rules belong at the neutral rules/"; fi

# Manifest lives under .foundry/ — never the legacy top-level path.
if [ -f "$REPO/.foundry-manifest.json" ]; then bad "legacy top-level .foundry-manifest.json — expected .foundry/manifest.json"; fi
manifest="$REPO/.foundry/manifest.json"
if [ ! -f "$manifest" ]; then
  bad ".foundry/manifest.json missing"
else
  if ! manifest_check="$(python3 - "$manifest" "${HARNESSES[@]}" 2>&1 <<'PY'
import json
import sys

path = sys.argv[1]
expected = sys.argv[2:]

try:
    with open(path, encoding="utf-8") as handle:
        manifest = json.load(handle)
except Exception as exc:
    print(f"manifest is not valid JSON: {exc}")
    sys.exit(1)

if manifest.get("conventionVersion") != 3:
    print(f"manifest conventionVersion={manifest.get('conventionVersion')!r}; expected 3")
    sys.exit(1)

harnesses = manifest.get("harnesses")
if not isinstance(harnesses, list) or any(not isinstance(item, str) for item in harnesses):
    print("manifest harnesses must be a string array")
    sys.exit(1)

if len(set(harnesses)) != len(harnesses):
    print("manifest harnesses contains duplicates")
    sys.exit(1)

expected_set = set(expected)
actual_set = set(harnesses)
missing = sorted(expected_set - actual_set)
extra = sorted(actual_set - expected_set)
if missing or extra:
    detail = []
    if missing:
        detail.append("missing " + ", ".join(missing))
    if extra:
        detail.append("extra " + ", ".join(extra))
    print("manifest harnesses mismatch: " + "; ".join(detail))
    sys.exit(1)
PY
  )"; then
    bad "$manifest_check"
  fi
fi

if [ "$fail" -eq 0 ]; then
  echo "harness-readability: PASS (${HARNESSES[*]})"
else
  echo "harness-readability: FAIL"
fi
exit "$fail"
