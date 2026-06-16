#!/usr/bin/env bash
# Tests for evals/harness/harness-readability-eval.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../evals/harness/harness-readability-eval.sh"
FIXTURE_ROOT="$(mktemp -d)"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

fail() { echo "FAIL: $1"; exit 1; }

make_fixture() {
  fixture="$(mktemp -d "$FIXTURE_ROOT/case.XXXXXX")"
  printf '# Instructions\n' > "$fixture/AGENTS.md"
  ln -s AGENTS.md "$fixture/CLAUDE.md"
  mkdir -p "$fixture/rules" "$fixture/.agents/plugins"
}

write_manifest() {
  local repo="$1"
  local harnesses_json="$2"
  local convention_version="${3:-3}"
  mkdir -p "$repo/.foundry"
  cat > "$repo/.foundry/manifest.json" <<EOF
{
  "pluginVersion": "1.0.0",
  "conventionVersion": $convention_version,
  "harnesses": $harnesses_json,
  "files": {}
}
EOF
}

make_fixture
write_manifest "$fixture" '["claude-code", "codex"]'
"$SCRIPT" "$fixture" claude-code codex >/dev/null \
  || fail "matching manifest harnesses should pass"

make_fixture
if "$SCRIPT" "$fixture" claude-code codex >/dev/null 2>&1; then
  fail "missing .foundry/manifest.json should fail"
fi

make_fixture
write_manifest "$fixture" '["claude-code"]'
if "$SCRIPT" "$fixture" claude-code codex >/dev/null 2>&1; then
  fail "manifest missing selected harness should fail"
fi

make_fixture
write_manifest "$fixture" '["claude-code", "codex", "extra"]'
if "$SCRIPT" "$fixture" claude-code codex >/dev/null 2>&1; then
  fail "manifest with unselected harness should fail"
fi

make_fixture
mkdir -p "$fixture/.foundry"
printf '{not json}\n' > "$fixture/.foundry/manifest.json"
if "$SCRIPT" "$fixture" claude-code codex >/dev/null 2>&1; then
  fail "invalid manifest json should fail"
fi

make_fixture
write_manifest "$fixture" '["claude-code", "codex"]' 2
if "$SCRIPT" "$fixture" claude-code codex >/dev/null 2>&1; then
  fail "manifest with old conventionVersion should fail"
fi

echo "harness_readability_test: PASS"
