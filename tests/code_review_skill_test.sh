#!/usr/bin/env bash
# Static and dry-run checks for the portable code-review skill.
# Hermetic: passes with codex/claude/tmux ABSENT. Drive harness detection with
# AGENT_HARNESS and stub tmux with AGENT_TMUX=/bin/echo; never spawns a session.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$REPO/plugins/foundry/skills/code-review"
SKILL_MD="$SKILL_DIR/SKILL.md"
DIMENSIONS="$SKILL_DIR/references/dimensions.md"
CONVERGENCE="$SKILL_DIR/references/convergence.md"
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
  [ -n "$SKILL_TEXT" ] || SKILL_TEXT="$(cat "$SKILL_MD" "$DIMENSIONS" "$CONVERGENCE" 2>/dev/null)"
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
grep -q "references/convergence.md" "$SKILL_MD" \
  || fail "code-review SKILL must link the convergence reference"

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
skill_grep "Metrics section\|names metrics" \
  || fail "docs-sync dimension must flag a design.md missing the Metrics section or its N/A"
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
skill_grep "commented-out\|early return" \
  || fail "code-review must grade a readability dimension (clean-code basics, advisory)"

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

# --- Calibration (agent precision) + spec grounding ------------------------
skill_grep "drop the finding" \
  || fail "calibration must require evidence (file:line) or drop the finding (AC-14.1)"
skill_grep "silence beats noise" \
  || fail "calibration must prefer silence to noise (AC-14.2)"
skill_grep "[Zz]ero findings" \
  || fail "calibration must allow zero findings as a valid outcome (AC-14.3)"
skill_grep "single finding" \
  || fail "calibration must cluster repeated patterns into a single finding (AC-14.4)"
skill_grep "callers" \
  || fail "calibration must read the context (callers/callees), not just the hunk (AC-14.5)"
skill_grep "deterministic tools" \
  || fail "calibration must leave style/lint to deterministic tools (AC-14.6)"
skill_grep "advisory unless" \
  || fail "calibration must set severity by verifiability (AC-14.7)"
skill_grep "conforms to the spec" \
  || fail "spec-grounding must not flag spec-conforming behavior (AC-15.1)"
skill_grep "invent a requirement" \
  || fail "spec-grounding must never invent a requirement (AC-15.2)"
skill_grep "hypothesis" \
  || fail "spec-grounding must treat a proposed fix as a hypothesis (AC-15.3)"

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

# --dry-run without --base shows the shared resolve_base (origin/HEAD -> main -> HEAD) range.
default_base="$("$REPO/plugins/foundry/scripts/spawn-fresh-session.sh" --resolve-base "$REPO" 2>/dev/null || true)"
if [ -n "$default_base" ]; then
  case "$dry_run" in
    *"$default_base..HEAD"*) ;;
    *) fail "dry-run without --base must show the resolve_base (origin/HEAD->main->HEAD) range" ;;
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

# --- Refuter selection (dry-run) -------------------------------------------
# --harness <family> forces the cross-model refuter on that family.
refuter_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run --harness codex roadmap/specs/code-review "$REPO"
)"
case "$refuter_run" in
  *refuter*codex*) ;;
  *) fail "--harness <family> must preview the cross-model refuter on that family" ;;
esac

# A 2-harness manifest derives the complementary refuter family (refuter-family.sh; AC-13.1).
mf_dir="$(mktemp -d)"; mkdir -p "$mf_dir/.foundry"
printf '%s\n' '{"harnesses": ["claude-code", "codex"], "files": {}}' > "$mf_dir/.foundry/manifest.json"
derived_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run roadmap/specs/code-review "$mf_dir"
)"
case "$derived_run" in
  *refuter*) ;;
  *) fail "a 2-harness manifest must derive a refuter family" ;;
esac

# A single-harness manifest (and no --harness) skips the refuter (single-agent).
sf_dir="$(mktemp -d)"; mkdir -p "$sf_dir/.foundry"
printf '%s\n' '{"harnesses": ["claude-code"], "files": {}}' > "$sf_dir/.foundry/manifest.json"
single_run="$(
  TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$SCRIPT" --dry-run roadmap/specs/code-review "$sf_dir"
)"
case "$single_run" in
  *"refuter skipped"*|*"single-agent"*|*"single agent"*) ;;
  *) fail "a single-harness manifest must skip the refuter and run single-agent" ;;
esac
rm -rf "$mf_dir" "$sf_dir"

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
