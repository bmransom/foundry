#!/usr/bin/env bash
# Tests for scripts/check-byte-identity.sh against a fixture tree.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../scripts/check-byte-identity.sh"
FIXTURE_ROOT="$(mktemp -d)"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

make_fixture() {
  fixture="$(mktemp -d "$FIXTURE_ROOT/case.XXXXXX")"
  mkdir -p "$fixture/plugins/foundry/templates/verbatim/scripts" "$fixture/scripts"
  printf '# foundry-template: tool v1\necho hello\n' > "$fixture/plugins/foundry/templates/verbatim/scripts/tool.sh"
  printf '# foundry-template: tool v1\necho hello\n' > "$fixture/scripts/tool.sh"
}

fail() { echo "FAIL: $1"; exit 1; }

make_fixture
"$SCRIPT" "$fixture" >/dev/null || fail "identical copy should pass"

make_fixture
printf 'echo hello\n' > "$fixture/scripts/tool.sh"   # marker line absent locally
"$SCRIPT" "$fixture" >/dev/null || fail "marker-only difference should pass"

make_fixture
printf '# foundry-template: tool v1\necho changed\n' > "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "drifted copy should fail"; fi

make_fixture
rm "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "missing copy should fail"; fi

make_fixture
printf '# foundry-template: tool v1\n' > "$fixture/plugins/foundry/templates/verbatim/scripts/tool.sh"
: > "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "marker-only template should fail"; fi

echo "byte_identity_test: PASS"
