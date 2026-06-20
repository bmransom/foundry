#!/usr/bin/env bash
# Unit checks for deterministic add/remove harness management helpers.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANAGE="$REPO/plugins/foundry/scripts/harness-manage.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$MANAGE" ] || fail "missing harness-manage.py"

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT
fixture_real="$(cd "$fixture" && pwd -P)"

mkdir -p "$fixture/.foundry"
cat >"$fixture/AGENTS.md" <<'EOF_AGENTS'
# AGENTS
EOF_AGENTS
ln -s AGENTS.md "$fixture/CLAUDE.md"
cat >"$fixture/.foundry/manifest.json" <<'EOF_MANIFEST'
{
  "pluginVersion": "0.2.0",
  "conventionVersion": 3,
  "harnesses": ["claude-code", "codex"],
  "files": {}
}
EOF_MANIFEST

before_manifest="$(shasum -a 256 "$fixture/.foundry/manifest.json" | awk '{print $1}')"
before_agents="$(shasum -a 256 "$fixture/AGENTS.md" | awk '{print $1}')"

status_out="$(python3 "$MANAGE" verify --dry-run "$fixture" 2>&1)"
after_verify_manifest="$(shasum -a 256 "$fixture/.foundry/manifest.json" | awk '{print $1}')"
[ "$before_manifest" = "$after_verify_manifest" ] || fail "verify mutated manifest"
grep -Fq "harness-status.py $fixture_real claude-code codex" <<<"$status_out" || fail "verify did not invoke harness-status"

remove_out="$(python3 "$MANAGE" remove "$fixture" claude-code 2>&1)"
grep -Fq "removed shim CLAUDE.md" <<<"$remove_out" || fail "did not report managed shim removal"
[ ! -e "$fixture/CLAUDE.md" ] || fail "managed CLAUDE.md shim remains"
[ -f "$fixture/AGENTS.md" ] || fail "shared AGENTS.md was deleted"
[ "$before_agents" = "$(shasum -a 256 "$fixture/AGENTS.md" | awk '{print $1}')" ] || fail "shared AGENTS.md changed"
python3 - "$fixture/.foundry/manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert manifest["harnesses"] == ["codex"], manifest["harnesses"]
PY

custom="$fixture/custom"
mkdir -p "$custom/.foundry"
cat >"$custom/AGENTS.md" <<'EOF_AGENTS'
# AGENTS
EOF_AGENTS
cat >"$custom/CLAUDE.md" <<'EOF_CLAUDE'
# Custom Claude guidance
EOF_CLAUDE
cat >"$custom/.foundry/manifest.json" <<'EOF_MANIFEST'
{"pluginVersion":"0.2.0","conventionVersion":3,"harnesses":["claude-code","codex"],"files":{}}
EOF_MANIFEST

custom_out="$(python3 "$MANAGE" remove "$custom" claude-code 2>&1)"
grep -Fq "custom shim CLAUDE.md left in place" <<<"$custom_out" || fail "custom shim was not reported"
[ -f "$custom/CLAUDE.md" ] || fail "custom shim was deleted"
python3 - "$custom/.foundry/manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert manifest["harnesses"] == ["codex"], manifest["harnesses"]
PY

last="$fixture/last"
mkdir -p "$last/.foundry"
cat >"$last/AGENTS.md" <<'EOF_AGENTS'
# AGENTS
EOF_AGENTS
cat >"$last/.foundry/manifest.json" <<'EOF_MANIFEST'
{"pluginVersion":"0.2.0","conventionVersion":3,"harnesses":["codex"],"files":{}}
EOF_MANIFEST

if python3 "$MANAGE" remove "$last" codex >"$last/remove.out" 2>&1; then
  fail "removed last harness"
fi
grep -Fq "refuse to remove the last harness" "$last/remove.out" || fail "last harness refusal missing"
python3 - "$last/.foundry/manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
assert manifest["harnesses"] == ["codex"], manifest["harnesses"]
PY

grep -Fq "harness-manage.py verify" "$REPO/plugins/foundry/skills/bootstrap/references/verify.md" || fail "bootstrap verify does not reference harness-manage.py verify"
grep -Fq "harness-status.py" "$REPO/plugins/foundry/skills/bootstrap/references/verify.md" || fail "bootstrap verify does not reference harness-status.py"
grep -Fq "harness-manage.py add" "$REPO/plugins/foundry/skills/update/references/add-harness.md" || fail "add-harness reference lacks add command"
grep -Fq "harness-manage.py remove" "$REPO/plugins/foundry/skills/update/references/add-harness.md" || fail "add-harness reference lacks remove command"
grep -Fq "harness-status.py" "$REPO/knowledge/validation.md" || fail "validation notes do not name harness-status.py"

echo "harness_management_test: PASS"
