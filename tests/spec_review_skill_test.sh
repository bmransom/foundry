#!/usr/bin/env bash
# Static and dry-run checks for the portable spec-review skill.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$REPO/plugins/foundry/skills/spec-review"
SKILL_MD="$SKILL_DIR/SKILL.md"
SCRIPT="$SKILL_DIR/scripts/spawn-spec-reviewer.sh"
CODE_SKILL="$REPO/plugins/foundry/skills/code/SKILL.md"
CLAUDE_AGENT="$REPO/plugins/foundry/agents/spec-reviewer.md"
README="$REPO/README.md"
SPEC_README="$REPO/roadmap/specs/README.md"
SEED_SPEC_RULE="$REPO/plugins/foundry/templates/seeds/rules/spec-conventions.md"
SEED_SPEC_README="$REPO/plugins/foundry/templates/seeds/roadmap/specs/README.md"
GITIGNORE="$REPO/.gitignore"

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

[ -f "$SKILL_MD" ] || fail "missing $SKILL_MD"
[ "$(frontmatter_value name "$SKILL_MD")" = "spec-review" ] \
  || fail "spec-review frontmatter name must match directory"
case "$(frontmatter_value description "$SKILL_MD")" in
  "Use when"*) ;;
  *) fail "spec-review description must start with 'Use when'" ;;
esac

grep -q "knowledge/glossary.md" "$SKILL_MD" \
  || fail "spec-review must read the glossary contract"
grep -q "AGENTS.md" "$SKILL_MD" \
  || fail "spec-review must read the repo writing-style contract"
grep -q "fresh context" "$SKILL_MD" \
  || fail "spec-review must prefer fresh context"
grep -q ".foundry/reports/spec-review/" "$SKILL_MD" \
  || fail "spec-review must define repo-local review output"
grep -q "scripts/spawn-spec-reviewer.sh" "$SKILL_MD" \
  || fail "spec-review must expose its fresh-context runner"

[ -x "$SCRIPT" ] || fail "spawn-spec-reviewer.sh must exist and be executable"
[ "$(AGENT_HARNESS=codex "$SCRIPT" --print-harness)" = "codex" ] \
  || fail "spawn-spec-reviewer.sh must detect AGENT_HARNESS=codex"

dry_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run roadmap/specs/example/design.md "$REPO"
)"
case "$dry_run" in
  *"new-window"*spec-review*claude*"roadmap/specs/example/design.md"*".foundry/reports/spec-review/"*) ;;
  *) fail "spawn-spec-reviewer.sh dry-run must launch claude review with target and report path" ;;
esac

grep -q "^\\.foundry/reports/$" "$GITIGNORE" \
  || fail ".gitignore must ignore generated Foundry reports"

grep -q "spec-review" "$CODE_SKILL" \
  || fail "code lifecycle must delegate to spec-review"
! grep -q "against \`spec-reviewer\`" "$CODE_SKILL" \
  || fail "code lifecycle must not name spec-reviewer as the canonical review surface"

grep -q "spec-review" "$CLAUDE_AGENT" \
  || fail "Claude spec-reviewer wrapper must delegate to spec-review"
grep -q "fresh context" "$CLAUDE_AGENT" \
  || fail "Claude spec-reviewer wrapper must state its fresh-context purpose"

for doc in "$README" "$SPEC_README" "$SEED_SPEC_RULE" "$SEED_SPEC_README"; do
  grep -q "spec-review" "$doc" \
    || fail "$doc must document spec-review as the canonical review surface"
done

! grep -q "Dispatch the \`spec-reviewer\` agent" "$SPEC_README" "$SEED_SPEC_RULE" "$SEED_SPEC_README" \
  || fail "current spec docs must not teach direct spec-reviewer dispatch"

echo "spec_review_skill_test: PASS"
