#!/usr/bin/env bash
# Launch a fresh-context, read-only code review of a change, then an optional
# cross-model refuter pass that drops the reviewer's false positives.
#
# Thin wrapper: it builds the prompts and the diff range, then delegates to
# Foundry's shared fresh-session runner (scripts/spawn-fresh-session.sh), which
# owns harness detection, tmux, and worktree isolation.
set -euo pipefail

plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

usage() {
  echo "usage: spawn-code-reviewer.sh [--dry-run] [--print-harness] [--skip-permissions] [--base <ref>] <spec-dir> [project-dir]" >&2
}

# The harness family complementary to the reviewer's — the refuter runs on a
# DIFFERENT family so it attacks correlated same-model false positives.
complementary_family() {
  case "$1" in
    claude) echo "codex" ;;
    codex) echo "claude" ;;
    pi) echo "codex" ;;
    *) echo "" ;;
  esac
}

main() {
  local runner="$(plugin_root)/scripts/spawn-fresh-session.sh"
  local dry_run=0 skip=0 base="" runner_args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1; runner_args+=("$1"); shift ;;
      --print-harness) exec "$runner" --print-harness ;;
      --skip-permissions|--yolo) skip=1; runner_args+=("$1"); shift ;;
      --base)
        [ "$#" -ge 2 ] || { usage; exit 2; }
        base="$2"; shift 2 ;;
      --) shift; break ;;
      -*) echo "spawn-code-reviewer: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done

  [ "$#" -ge 1 ] || { usage; exit 2; }
  local spec_dir="$1"
  local dir="${2:-$PWD}"

  # Diff base: --base overrides; default is the merge-base of main and HEAD.
  # Report the empty range and review the working diff rather than nothing.
  if [ -z "$base" ]; then
    base="$(git -C "$dir" merge-base main HEAD 2>/dev/null || true)"
  fi
  local range
  if [ -n "$base" ]; then range="$base..HEAD"; else range="(no merge-base — review the working diff)"; fi

  local review_dir=".foundry/reports/code-review"
  # Absolute report path under the PRIMARY tree, so retiring the spawned
  # session's worktree cannot delete the report (the harness cwd is the
  # worktree after isolation).
  local report="$dir/$review_dir/$(date +%Y%m%d%H%M%S)-code-review.md"

  local prompt
  prompt="Use the code-review skill at $(plugin_root)/skills/code-review/SKILL.md to review the change for spec $spec_dir in fresh context. This is READ-ONLY: do not edit any file. Diff range: $range. Read the spec files, the diff, roadmap/ROADMAP.md, knowledge/validation.md, and knowledge/glossary.md; run python3 scripts/knowledge.py check yourself. Grade every dimension from artifacts you read or commands you run, never from the author's claims. End the report with the findings body, then the FLAGGED: footer (one line per flagged finding), then a single final line CODE_REVIEW: PASS or CODE_REVIEW: FAIL. Write the complete report to the absolute path $report."

  [ "$dry_run" -eq 1 ] || mkdir -p "$dir/$review_dir"

  # Harness detection has one source: the shared runner.
  local reviewer_family
  reviewer_family="$("$runner" --print-harness)"

  if [ "$dry_run" -eq 1 ]; then
    # AC-1.5: name the harness, spec dir, diff range, fresh-session prompt path,
    # and report path. The shared runner echoes the concrete prompt file path.
    echo "code-review launch: harness=$reviewer_family spec-dir=$spec_dir range=$range"
    echo "report: $report"
  fi

  printf '%s\n' "$prompt" |
    "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review "$dir"
  [ "$dry_run" -eq 1 ] || echo "report: $report"

  # --- Cross-model refuter pass (T11) -------------------------------------
  # The refuter runs on a DIFFERENT harness family than the reviewer, read-only,
  # over ONLY the candidate FLAGGED findings and the diff — never the report
  # prose. It is DROP-only (never adds a finding). When only one harness family
  # is available, skip it and run the reviewer single-agent.
  local complementary
  complementary="$(complementary_family "$reviewer_family")"

  # The set of harness families available for the refuter. Default to both
  # common families; FOUNDRY_REFUTER_FAMILIES overrides for tests and for repos
  # that expose only one family.
  local families="${FOUNDRY_REFUTER_FAMILIES:-claude codex}"
  if ! printf '%s\n' $families | grep -qxF "$complementary" || [ -z "$complementary" ]; then
    echo "refuter skipped: only one harness family available — reviewer runs single-agent"
    return 0
  fi

  local refuter_prompt
  refuter_prompt="Use the code-review skill's REFUTER contract at $(plugin_root)/skills/code-review/SKILL.md. You are a single asymmetric refute pass — NOT a debate. You receive ONLY the candidate FLAGGED findings from $report and the diff for range $range; you do NOT see the reviewer's reasoning. READ-ONLY: edit nothing. Per candidate finding, KEEP it only if you can produce concrete evidence it is real, else mark it DROP. You may only REMOVE a finding, never ADD one. Output one line per candidate finding: KEEP <signature> or DROP <signature>."

  if [ "$dry_run" -eq 1 ]; then
    echo "refuter: spawn on complementary family $complementary (read-only, candidate findings + diff only)"
    echo "refuter prompt: $refuter_prompt"
  fi
  printf '%s\n' "$refuter_prompt" |
    AGENT_HARNESS="$complementary" "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review-refuter "$dir"
  [ "$dry_run" -eq 1 ] || echo "refuter: ran on complementary family $complementary; final footer = candidates minus DROPs"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
