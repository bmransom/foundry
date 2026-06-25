#!/usr/bin/env bash
# Manifest parity: the Claude and Codex plugin manifests must declare the same version.
# release-please bumps both via extra-files; this gate catches drift if that config breaks
# (the Codex manifest silently rotted to 0.1.0 vs 0.1.6 before this guard existed).
set -euo pipefail
REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
ver() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$1"; }
claude_v="$(ver "$REPO/plugins/foundry/.claude-plugin/plugin.json")"
codex_v="$(ver "$REPO/plugins/foundry/.codex-plugin/plugin.json")"
if [ "$claude_v" != "$codex_v" ]; then
  echo "manifest-parity: MISMATCH — .claude-plugin=$claude_v .codex-plugin=$codex_v (release-please must bump both)" >&2
  exit 1
fi
echo "manifest-parity: OK ($claude_v)"
