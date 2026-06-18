#!/usr/bin/env bash
# Static checks for plugin-resident skills.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO/plugins/foundry/skills"

required_skills=(
  bootstrap
  code
  design-patterns
  extract-skill
  handoff
  modular-structure
  naming-standards
  performance
  spec-review
  update
)

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

frontmatter_value() {
  local key="$1" file="$2"
  awk -v key="$key" '
    NR == 1 && $0 != "---" { exit }
    NR > 1 && $0 == "---" { exit }
    NR > 1 && index($0, key ":") == 1 {
      sub("^[^:]+:[[:space:]]*", "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$file"
}

for skill in "${required_skills[@]}"; do
  skill_md="$SKILLS_DIR/$skill/SKILL.md"
  [ -f "$skill_md" ] || fail "missing $skill_md"
  [ "$(frontmatter_value name "$skill_md")" = "$skill" ] \
    || fail "$skill_md frontmatter name must match directory"
  description="$(frontmatter_value description "$skill_md")"
  [ -n "$description" ] || fail "$skill_md missing description"
  case "$description" in
    "Use when"*) ;;
    *) fail "$skill_md description must start with 'Use when'" ;;
  esac
done

[ ! -d "$SKILLS_DIR/reference-gap-profiling" ] \
  || fail "reference-gap-profiling should be consolidated into performance"
[ ! -d "$SKILLS_DIR/performance-comparison" ] \
  || fail "performance-comparison should be consolidated into performance"
grep -q "main.*feature" "$SKILLS_DIR/performance/SKILL.md" \
  || fail "performance must cover main vs feature baselines"
grep -q "flag-off.*flag-on" "$SKILLS_DIR/performance/SKILL.md" \
  || fail "performance must cover feature flag baselines"

for lifecycle_skill in performance naming-standards design-patterns modular-structure; do
  grep -q "$lifecycle_skill" "$SKILLS_DIR/code/SKILL.md" \
    || fail "code lifecycle must delegate to $lifecycle_skill"
done

for pattern in Strategy Observer Adapter; do
  grep -q "$pattern" "$SKILLS_DIR/design-patterns/SKILL.md" \
    || fail "design-patterns must include $pattern"
done

grep -q "directory" "$SKILLS_DIR/modular-structure/SKILL.md" \
  || fail "modular-structure must cover directory layout"

echo "plugin_skills_test: PASS"
