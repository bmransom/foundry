#!/usr/bin/env bash
# cross-family-review.sh: derive the complementary harness family + spawn one
# context-isolated pass, or skip ("none") when single-family. Hermetic — the spawn is
# stubbed via CROSS_FAMILY_SPAWN_CMD, so no tmux / LLM.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFR="$REPO/plugins/foundry/scripts/cross-family-review.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$CFR" ] || fail "missing executable cross-family-review.sh"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cat > "$work/stub" <<'S'
#!/usr/bin/env bash
echo "spawned:$1" > "$2"
S
chmod +x "$work/stub"

run() {  # $1 dir -> sets RC, OUT
  set +e
  OUT="$(CROSS_FAMILY_SPAWN_CMD="$work/stub" bash "$CFR" claude "$1" cross-fam "$work/report" "a prompt" 2>&1)"
  RC=$?
  set -e
}

# Arm 1 — multi-family manifest: derive codex, spawn, print the family.
mkdir -p "$work/multi/.foundry"
printf '{ "harnesses": ["claude-code", "codex"] }\n' > "$work/multi/.foundry/manifest.json"
run "$work/multi"
[ "$RC" -eq 0 ] || fail "multi: rc $RC: $OUT"
[ "$(tail -1 <<<"$OUT")" = codex ] || fail "multi: expected codex, got: $OUT"
grep -q 'spawned:codex' "$work/report" || fail "multi: stub should have spawned on codex"

# Arm 2 — single-family manifest: none, never spawns.
rm -f "$work/report"
mkdir -p "$work/single/.foundry"
printf '{ "harnesses": ["claude-code"] }\n' > "$work/single/.foundry/manifest.json"
run "$work/single"
[ "$(tail -1 <<<"$OUT")" = none ] || fail "single: expected none, got: $OUT"
[ ! -f "$work/report" ] || fail "single: must NOT spawn"

# Arm 3 — no manifest: none.
mkdir -p "$work/nomani"
run "$work/nomani"
[ "$(tail -1 <<<"$OUT")" = none ] || fail "no-manifest: expected none, got: $OUT"

echo "cross_family_review_test: PASS"
