#!/usr/bin/env bash
# Deliverables outlive the worktree: the spec-review and extract-skill wrappers
# put an ABSOLUTE deliverable path rooted at the primary project dir ($dir) in
# the prompt, so a file written there survives `worktree-retire.sh`.
#
# Hermetic: AGENT_TMUX=/bin/echo, TMUX=1. No real claude/codex/tmux required.
set -euo pipefail

# Hermetic against the git-hook environment: a hook exports GIT_DIR/GIT_WORK_TREE
# etc., which would hijack `git init` of the fixture repos below. Clear them.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_PREFIX \
      GIT_CONFIG_PARAMETERS GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO/plugins/foundry/scripts/spawn-fresh-session.sh"
SPEC="$REPO/plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh"
EXTRACT="$REPO/plugins/foundry/skills/extract-skill/scripts/spawn-extractor.sh"
RETIRE="$REPO/scripts/worktree-retire.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

scratch="$(mktemp -d)"
repo="$scratch/repo"
trap '
  for w in "$repo"/.foundry/tmp/fresh-session/*/worktree; do
    [ -d "$w" ] && git -C "$repo" worktree remove --force "$w" 2>/dev/null || true
  done
  git -C "$repo" worktree prune 2>/dev/null || true
  rm -rf "$scratch"
' EXIT

git init -q -b main "$repo"
git -C "$repo" config user.email "foundry@example.test"
git -C "$repo" config user.name "Foundry Test"
printf '.foundry/tmp/\n.foundry/reports/\n' > "$repo/.gitignore"
printf '# fixture\n' > "$repo/README.md"
git -C "$repo" add .gitignore README.md
git -C "$repo" commit -qm "initial"

prompt_of() {  # session prompt file for the most recent spawn
  find "$repo/.foundry/tmp/fresh-session" -name prompt.md -print0 \
    | xargs -0 ls -t 2>/dev/null | head -1
}
launch_worktree() {  # the worktree cwd from a captured launch line
  printf '%s\n' "$1" | grep new-window \
    | awk '{for (i=1;i<NF;i++) if ($i=="-c") {print $(i+1); exit}}'
}

# --- AC-4.1: spec-review prompt carries an ABSOLUTE report path under $dir.
spec_out="$(TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$SPEC" "$repo/README.md" "$repo")"
spec_prompt="$(prompt_of)"
[ -f "$spec_prompt" ] || fail "spec-review must write a prompt file"
grep -q "$repo/.foundry/reports/spec-review/" "$spec_prompt" \
  || fail "AC-4.1: spec-review prompt must carry an absolute report path under \$dir"
# The path must NOT be relative to the worktree cwd.
spec_wt="$(launch_worktree "$spec_out")"
grep -qE "(^|[^/])\.foundry/reports/spec-review/" "$spec_prompt" \
  && ! grep -q "$repo/.foundry/reports/spec-review/" "$spec_prompt" \
  && fail "AC-4.1: the report path must be absolute, not relative to the worktree cwd"

# Simulate the deliverable the spawned agent would write to the primary tree.
report_path="$(grep -oE "$repo/.foundry/reports/spec-review/[^ ]+\.md" "$spec_prompt" | head -1)"
[ -n "$report_path" ] || fail "AC-4.1: could not extract the absolute report path"
mkdir -p "$(dirname "$report_path")"
printf '# spec review report\n' > "$report_path"

# --- AC-4.1: extract-skill prompt carries an ABSOLUTE draft path under $dir.
mkdir -p "$repo/.agent/skill-extractions/demo"
printf 'brief\n' > "$repo/.agent/skill-extractions/demo/brief.md"
extract_out="$(TMUX=1 AGENT_HARNESS=codex AGENT_TMUX=/bin/echo "$EXTRACT" demo "$repo/.agent/skill-extractions/demo/brief.md" "$repo")"
extract_prompt="$(prompt_of)"
[ -f "$extract_prompt" ] || fail "extract-skill must write a prompt file"
draft_path="$(grep -oE "$repo/[^ ]+\.md" "$extract_prompt" | grep -v 'prompt.md' | grep -iE 'draft|skill' | head -1)"
[ -n "$draft_path" ] || fail "AC-4.1: extract-skill prompt must carry an absolute draft path under \$dir"
case "$draft_path" in
  "$repo"/*) ;;
  *) fail "AC-4.1: the extract draft path must be absolute under \$dir (got $draft_path)" ;;
esac
extract_wt="$(launch_worktree "$extract_out")"
case "$draft_path" in
  "$extract_wt"/*) fail "AC-4.1: the draft path must be in the primary tree, not the worktree" ;;
esac
mkdir -p "$(dirname "$draft_path")"
printf '# skill draft\n' > "$draft_path"

# --- AC-4.2: retiring the worktrees does NOT delete the deliverables.
# Run retire from within the owning repo so git resolves the worktree.
for wt in "$spec_wt" "$extract_wt"; do
  case "$wt" in
    "$repo"/.foundry/tmp/fresh-session/*/worktree)
      ( cd "$repo" && "$RETIRE" "$wt" ) >/dev/null 2>&1 || fail "retire failed for $wt" ;;
  esac
done

[ -f "$report_path" ] || fail "AC-4.2: spec-review report must survive worktree retire"
[ -f "$draft_path" ]  || fail "AC-4.2: extract-skill draft must survive worktree retire"

echo "fresh_session_deliverables_test: PASS"
