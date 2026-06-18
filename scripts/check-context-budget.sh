#!/usr/bin/env bash
# Context-budget lint: flags plugin-resident prose files that exceed their line budgets.
# Plugin prose loads into context windows; oversized files waste tokens in every session.
# Usage: check-context-budget.sh [repo-root]   (defaults to this repo)
#
# Budgets calibrated 2026-06-11: code skill 100 lines, plugin agent 41 lines, seed rule 34 lines.
# Headroom added to tolerate organic growth before a forced trim.
set -euo pipefail
REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

SKILL_BUDGET=120   # plugins/foundry/skills/*/SKILL.md
AGENT_BUDGET=60    # plugins/foundry/agents/*.md
RULE_BUDGET=60     # plugins/foundry/templates/seeds/rules/*.md

SKILLS_DIR="$REPO/plugins/foundry/skills"
AGENTS_DIR="$REPO/plugins/foundry/agents"
RULES_DIR="$REPO/plugins/foundry/templates/seeds/rules"

has_violation=0

check_file() {
  local path="$1" budget="$2"
  local lines
  lines="$(awk 'END{print NR}' "$path")"
  if [ "$lines" -gt "$budget" ]; then
    echo "context-budget: OVER ${path#"$REPO/"} ($lines > $budget)"
    has_violation=1
  fi
}

if [ -d "$SKILLS_DIR" ]; then
  while IFS= read -r -d '' skill_file; do
    check_file "$skill_file" "$SKILL_BUDGET"
  done < <(find "$SKILLS_DIR" -name 'SKILL.md' -print0)
fi

if [ -d "$AGENTS_DIR" ]; then
  agent_files=("$AGENTS_DIR"/*.md)
  if [ -e "${agent_files[0]}" ]; then
    for agent_file in "${agent_files[@]}"; do
      check_file "$agent_file" "$AGENT_BUDGET"
    done
  fi
fi

if [ -d "$RULES_DIR" ]; then
  rule_files=("$RULES_DIR"/*.md)
  if [ -e "${rule_files[0]}" ]; then
    for rule_file in "${rule_files[@]}"; do
      check_file "$rule_file" "$RULE_BUDGET"
    done
  fi
fi

[ "$has_violation" -eq 0 ] && echo "context-budget: PASS"
exit "$has_violation"
