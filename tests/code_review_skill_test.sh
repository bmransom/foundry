#!/usr/bin/env bash
# Static and dry-run checks for the portable code-review skill.
# Hermetic: passes with codex/claude/tmux ABSENT. Drive harness detection with
# AGENT_HARNESS and stub tmux with AGENT_TMUX=/bin/echo; never spawns a session.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$REPO/plugins/foundry/skills/code-review"
SKILL_MD="$SKILL_DIR/SKILL.md"
DIMENSIONS="$SKILL_DIR/references/dimensions.md"
SCRIPT="$SKILL_DIR/scripts/spawn-code-reviewer.sh"
CODE_SKILL="$REPO/plugins/foundry/skills/code/SKILL.md"
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

# The skill text the reviewer reads: SKILL.md plus its references. Concatenated
# into a single file so grep -q exiting early on a match cannot SIGPIPE a pipe
# (pipefail would then misread the match as a failure).
SKILL_TEXT=""
skill_grep() {
  [ -n "$SKILL_TEXT" ] || SKILL_TEXT="$(cat "$SKILL_MD" "$DIMENSIONS" 2>/dev/null)"
  grep -q "$1" <<<"$SKILL_TEXT"
}

# --- Frontmatter -----------------------------------------------------------
[ -f "$SKILL_MD" ] || fail "missing $SKILL_MD"
[ "$(frontmatter_value name "$SKILL_MD")" = "code-review" ] \
  || fail "code-review frontmatter name must match directory"
case "$(frontmatter_value description "$SKILL_MD")" in
  "Use when"*) ;;
  *) fail "code-review description must start with 'Use when'" ;;
esac

# --- Contract reads --------------------------------------------------------
skill_grep "knowledge/glossary.md" \
  || fail "code-review must read the glossary contract"
skill_grep "AGENTS.md" \
  || fail "code-review must read the AGENTS.md contract"
skill_grep "fresh context" \
  || fail "code-review must prefer fresh context"
skill_grep "knowledge/validation.md" \
  || fail "code-review must read the validation contract for lifecycle evidence"
skill_grep "roadmap/ROADMAP.md" \
  || fail "code-review must read the board for lifecycle evidence"

# --- Surfaces --------------------------------------------------------------
skill_grep ".foundry/reports/code-review/" \
  || fail "code-review must name its repo-local report output"
skill_grep "scripts/spawn-code-reviewer.sh" \
  || fail "code-review must expose its fresh-context runner"

# --- Output contract -------------------------------------------------------
skill_grep "CODE_REVIEW: PASS" \
  || fail "code-review must define the PASS verdict line"
skill_grep "CODE_REVIEW: FAIL" \
  || fail "code-review must define the FAIL verdict line"
skill_grep "FLAGGED:" \
  || fail "code-review must define the FLAGGED footer"
for field in severity dimension "file:line" evidence problem fix; do
  skill_grep "$field" \
    || fail "code-review finding must carry $field"
done

# --- Dimensions (evidence, not self-claims) --------------------------------
skill_grep "knowledge.py check" \
  || fail "docs-sync dimension must RUN knowledge.py check, not trust the report"
skill_grep "AC . Scenario . test . code\|AC → Scenario → test → code" \
  || fail "complete-implementation dimension must name the AC->Scenario->test->code matrix"
skill_grep "Replaces" \
  || fail "domain-language dimension must spare debt terms inside a glossary Replaces column"
skill_grep "diagram" \
  || fail "docs-sync dimension must verify design.md diagrams against the code (AC-3.5)"
skill_grep "Wide event" \
  || fail "logging-consistency dimension must name the Wide event"
skill_grep "print --help" \
  || fail "logging-consistency must spare a legitimate CLI surface like print --help"
skill_grep "advisory" \
  || fail "size tripwires must be advisory, never a hard fail"
skill_grep "400\|800\|250\|80" \
  || fail "size tripwires must name the LOC thresholds"
skill_grep "discriminat" \
  || fail "robust-tests dimension must require tests that discriminate a seeded defect"
skill_grep "[Pp]erformance\|efficien" \
  || fail "code-review must grade a performance/efficiency dimension"

# --- Refuter contract ------------------------------------------------------
skill_grep "refuter\|refute\|Refuter" \
  || fail "code-review must define the cross-model refuter pass"
skill_grep "DROP" \
  || fail "refuter must be DROP-only"
skill_grep "harness family\|harness-family" \
  || fail "refuter must run on a different harness family"
skill_grep "single asymmetric\|not a debate\|not a symmetric debate\|asymmetric" \
  || fail "refuter must be a single asymmetric pass, not a debate"
skill_grep "single-agent\|single agent\|skip" \
  || fail "refuter must skip and run single-agent when one harness family is available"

# --- Runner: executable, harness detection, hermetic dry-runs --------------
[ -x "$SCRIPT" ] || fail "spawn-code-reviewer.sh must exist and be executable"
[ "$(AGENT_HARNESS=codex "$SCRIPT" --print-harness)" = "codex" ] \
  || fail "spawn-code-reviewer.sh --print-harness must honor AGENT_HARNESS=codex"

# --print-harness exits without spawning: no report written, no session launched.
# Guard the find: a missing reports dir must count as 0, never a pipefail.
report_count() {
  local dir="$REPO/.foundry/reports/code-review"
  [ -d "$dir" ] || { echo 0; return; }
  find "$dir" -type f | wc -l | tr -d ' '
}
before="$(report_count)"
ph_out="$(AGENT_HARNESS=codex AGENT_TMUX=/bin/false "$SCRIPT" --print-harness)"
[ "$ph_out" = "codex" ] || fail "--print-harness must print only the harness"
after="$(report_count)"
[ "$before" = "$after" ] || fail "--print-harness must not write a report"

# A --dry-run carries harness + spec dir + diff range + prompt path + report path.
dry_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run roadmap/specs/code-review "$REPO"
)"
case "$dry_run" in
  *"new-window"*code-review*claude*) ;;
  *) fail "dry-run must launch a claude code-review session via tmux" ;;
esac
case "$dry_run" in
  *"roadmap/specs/code-review"*) ;;
  *) fail "dry-run must name the spec dir" ;;
esac
case "$dry_run" in
  *".foundry/tmp/fresh-session/"*"prompt.md"*) ;;
  *) fail "dry-run must name the fresh-session prompt path" ;;
esac
case "$dry_run" in
  *".foundry/reports/code-review/"*"-code-review.md"*) ;;
  *) fail "dry-run must name the report path" ;;
esac

# --dry-run without --base shows the git merge-base main HEAD default range.
default_base="$(git -C "$REPO" merge-base main HEAD 2>/dev/null || true)"
if [ -n "$default_base" ]; then
  case "$dry_run" in
    *"$default_base"*"..HEAD"*|*"$default_base..HEAD"*) ;;
    *) fail "dry-run without --base must show the git merge-base main HEAD default range" ;;
  esac
fi

# --dry-run --base <ref> overrides the range.
override_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run --base FEEDFACE roadmap/specs/code-review "$REPO"
)"
case "$override_run" in
  *"FEEDFACE..HEAD"*) ;;
  *) fail "--dry-run --base <ref> must show the overridden range" ;;
esac

# --skip-permissions (and its --yolo alias) pass the bypass to the shared runner.
for flag in --skip-permissions --yolo; do
  skip_run="$(
    TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
      "$SCRIPT" --dry-run "$flag" roadmap/specs/code-review "$REPO"
  )"
  case "$skip_run" in
    *"--dangerously-skip-permissions"*) ;;
    *) fail "--dry-run $flag must pass the permission bypass to the shared runner" ;;
  esac
done

# --- Refuter dry-run behavior ----------------------------------------------
# With two harness families reachable, the dry-run shows the refuter on the
# complementary family with a read-only, candidate-findings-only prompt.
refuter_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run roadmap/specs/code-review "$REPO"
)"
case "$refuter_run" in
  *refuter*) ;;
  *) fail "dry-run must preview the cross-model refuter spawn" ;;
esac

# With only one harness family available, the refuter is skipped (single-agent).
single_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo FOUNDRY_REFUTER_FAMILIES=claude \
    "$SCRIPT" --dry-run roadmap/specs/code-review "$REPO"
)"
case "$single_run" in
  *"refuter skipped"*|*"single-agent"*|*"single agent"*) ;;
  *) fail "dry-run with one harness family must skip the refuter and run single-agent" ;;
esac

# --- Lifecycle delegation --------------------------------------------------
grep -q "code-review" "$CODE_SKILL" \
  || fail "code lifecycle must delegate to code-review as the Review stage"
grep -q "6 Review" "$CODE_SKILL" \
  || fail "code lifecycle must add a numbered Review stage (6 Review)"
grep -q "7 Finish" "$CODE_SKILL" \
  || fail "code lifecycle must renumber Finish to 7 after inserting Review"

# --- Reports are gitignored ------------------------------------------------
grep -q "^\\.foundry/reports/$" "$GITIGNORE" \
  || fail ".gitignore must ignore generated Foundry reports"

echo "code_review_skill_test: PASS"
