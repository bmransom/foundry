#!/usr/bin/env bash
# Tests for scripts/check-skill-references.sh against fixture skill trees.
# The lint must catch an orphaned reference yet pass a two-level disclosure
# chain (SKILL.md -> registry -> playbook), so it cannot be satisfied by a naive
# "every reference appears in SKILL.md" check.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../scripts/check-skill-references.sh"

fail() { echo "FAIL: $1"; exit 1; }

# Case (a): SKILL.md links its only reference → PASS.
F="$(mktemp -d)"; trap 'rm -rf "$F"' EXIT
mkdir -p "$F/good/references"
printf '# Good\nSee `references/a.md`.\n' > "$F/good/SKILL.md"
echo a > "$F/good/references/a.md"
"$SCRIPT" "$F" >/dev/null || fail "a linked reference should pass"

# Case (b): a reference present but unlinked → FAIL, naming the orphan.
F="$(mktemp -d)"
mkdir -p "$F/orphan/references"
printf '# Orphan\nSee `references/linked.md`.\n' > "$F/orphan/SKILL.md"
echo linked   > "$F/orphan/references/linked.md"
echo dangling > "$F/orphan/references/dangling.md"
out="$("$SCRIPT" "$F" 2>&1 || true)"
if "$SCRIPT" "$F" >/dev/null 2>&1; then fail "an orphaned reference should fail"; fi
echo "$out" | grep -q "dangling.md" || fail "output must name the orphan (got: $out)"
rm -rf "$F"

# Case (c): two-level chain SKILL.md -> README -> playbook (relative link) → PASS.
F="$(mktemp -d)"
mkdir -p "$F/chain/references/migrations"
printf '# Chain\nRead `references/migrations/README.md`.\n' > "$F/chain/SKILL.md"
printf '# Registry\nPlaybook: [p1.md](p1.md)\n' > "$F/chain/references/migrations/README.md"
echo p1 > "$F/chain/references/migrations/p1.md"
"$SCRIPT" "$F" >/dev/null || fail "a two-level disclosure chain should pass"
rm -rf "$F"

# Case (d): a reference reached through a root-relative token inside a reference → PASS.
F="$(mktemp -d)"
mkdir -p "$F/root/references"
printf '# Root\nSee `references/a.md`.\n' > "$F/root/SKILL.md"
printf 'then `references/b.md`\n' > "$F/root/references/a.md"
echo b > "$F/root/references/b.md"
"$SCRIPT" "$F" >/dev/null || fail "a root-relative token inside a reference should resolve"
rm -rf "$F"

# Case (e): a skill with no references/ directory → PASS (nothing to lint).
F="$(mktemp -d)"
mkdir -p "$F/bare"
printf '# Bare\nNo references here.\n' > "$F/bare/SKILL.md"
"$SCRIPT" "$F" >/dev/null || fail "a skill without references should pass"
rm -rf "$F"

echo "skill_references_test: PASS"
