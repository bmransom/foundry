#!/usr/bin/env bash
# Run a fresh-context, read-only code review SYNCHRONOUSLY: spawn the reviewer, block
# until its report is written (wait-for-report.sh), compute the verdict from the
# FLAGGED footer (never the reviewer's forgeable verdict line), then run the
# cross-model refuter over ONLY the footer + diff and recompute the footer to
# candidates-minus-DROPs. A timed-out or never-written report FAILS — never a false
# PASS. Read-only: this runner never edits the consumer repo and never fixes findings.
#
# Thin wrapper: it builds the prompts and the diff range, then delegates each spawn to
# Foundry's shared fresh-session runner (scripts/spawn-fresh-session.sh), which owns
# harness detection, tmux, and worktree isolation. The footer algebra, the synchronous
# wait, and the verdict recompute live in sibling scripts.
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

# Spawn one fresh-context session (role = reviewer|refuter) that writes its artifact
# to $out. CODE_REVIEW_SPAWN_CMD is a test-only seam: a stub that writes $out in place
# of the real detached spawn. Production pipes the prompt to the shared runner. Relies
# on main()'s locals (runner, runner_args, complementary, dir) via dynamic scope.
spawn_session() {
  local role="$1" out="$2" prompt="$3"
  if [ -n "${CODE_REVIEW_SPAWN_CMD:-}" ]; then
    "$CODE_REVIEW_SPAWN_CMD" "$role" "$out"
    return
  fi
  if [ "$role" = refuter ]; then
    printf '%s\n' "$prompt" | AGENT_HARNESS="$complementary" "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review-refuter "$dir"
  else
    printf '%s\n' "$prompt" | "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review "$dir"
  fi
}

main() {
  local script_dir; script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local runner; runner="$(plugin_root)/scripts/spawn-fresh-session.sh"
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

  # Diff base: --base overrides; default is the merge-base of main and HEAD (T23
  # swaps this for the shared resolver). Review the working diff if there is none.
  if [ -z "$base" ]; then
    base="$(git -C "$dir" merge-base main HEAD 2>/dev/null || true)"
  fi
  local range
  if [ -n "$base" ]; then range="$base..HEAD"; else range="(no merge-base — review the working diff)"; fi

  local review_dir=".foundry/reports/code-review"
  # Absolute report path under the PRIMARY tree, so retiring a spawned worktree
  # cannot delete the report (the harness cwd is the worktree after isolation).
  local report="$dir/$review_dir/$(date +%Y%m%d%H%M%S)-code-review.md"

  local prompt
  prompt="Use the code-review skill at $(plugin_root)/skills/code-review/SKILL.md to review the change for spec $spec_dir in fresh context. This is READ-ONLY: do not edit any file. Diff range: $range. Read the spec files, the diff, roadmap/ROADMAP.md, knowledge/validation.md, and knowledge/glossary.md; run python3 scripts/knowledge.py check yourself. Grade every dimension from artifacts you read or commands you run, never from the author's claims. End the report with the findings body, then the FLAGGED: footer (one line per BLOCKING finding), then a single final line CODE_REVIEW: PASS or CODE_REVIEW: FAIL. Write the complete report to the absolute path $report."

  # Harness detection has one source: the shared runner (CODE_REVIEW_REVIEWER_FAMILY
  # overrides it for deterministic tests).
  local reviewer_family
  reviewer_family="${CODE_REVIEW_REVIEWER_FAMILY:-$("$runner" --print-harness)}"
  local complementary; complementary="$(complementary_family "$reviewer_family")"
  # Families available for the refuter; FOUNDRY_REFUTER_FAMILIES overrides for tests
  # and single-family repos (T23 swaps this for refuter-family.sh / the manifest).
  local families="${FOUNDRY_REFUTER_FAMILIES:-claude codex}"
  local refuter_on=0
  if [ -n "$complementary" ] && printf '%s\n' $families | grep -qxF "$complementary"; then refuter_on=1; fi

  local refuter_head="Use the code-review skill's REFUTER contract at $(plugin_root)/skills/code-review/SKILL.md. You are a single asymmetric refute pass — NOT a debate. READ-ONLY: edit nothing. You receive ONLY the candidate FLAGGED findings and the diff for range $range; you do NOT see the reviewer's reasoning. Per candidate finding, KEEP it only with concrete evidence it is real, else mark it DROP. You may only REMOVE a finding, never ADD one."

  # --- Dry run: preview every launch, spawn nothing, wait for nothing. --------
  if [ "$dry_run" -eq 1 ]; then
    echo "code-review launch: harness=$reviewer_family spec-dir=$spec_dir range=$range"
    echo "report: $report"
    printf '%s\n' "$prompt" | "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review "$dir"
    echo "report: $report"
    if [ "$refuter_on" -eq 1 ]; then
      echo "refuter: spawn on complementary family $complementary (read-only, candidate findings + diff only)"
      printf '%s\n' "$refuter_head Output one line per candidate finding (KEEP <signature> or DROP <signature>), then a final line REFUTER: DONE." \
        | AGENT_HARNESS="$complementary" "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review-refuter "$dir"
      echo "refuter: previewed on complementary family $complementary; final footer = candidates minus DROPs"
    else
      echo "refuter skipped: only one harness family available — reviewer runs single-agent"
    fi
    return 0
  fi

  # --- Real run: synchronous spawn -> wait -> compute -> refuter -> recompute --
  local wait_timeout="${CODE_REVIEW_WAIT_TIMEOUT:-300}" wait_poll="${CODE_REVIEW_WAIT_POLL:-1}"
  mkdir -p "$dir/$review_dir"

  spawn_session reviewer "$report" "$prompt"
  if ! "$script_dir/wait-for-report.sh" "$report" "$wait_timeout" "$wait_poll"; then
    echo "code-review: reviewer report did not complete within ${wait_timeout}s — FAIL (not converged)" >&2
    exit 1
  fi
  echo "report: $report"

  local refuter_out=/dev/null
  if [ "$refuter_on" -eq 1 ]; then
    local footer_payload; footer_payload="$("$script_dir/footer-algebra.sh" union "$report")"
    refuter_out="$report.refuter"
    local refuter_prompt="$refuter_head
Candidate FLAGGED findings:
$footer_payload
Write one line per candidate finding (KEEP <signature> or DROP <signature>), then a final line REFUTER: DONE, to the absolute path $refuter_out."
    spawn_session refuter "$refuter_out" "$refuter_prompt"
    if ! "$script_dir/wait-for-report.sh" "$refuter_out" "$wait_timeout" "$wait_poll" '^REFUTER: DONE$'; then
      echo "refuter did not complete within ${wait_timeout}s — keeping all reviewer findings (no DROPs)" >&2
      refuter_out=/dev/null
    fi
  else
    echo "refuter skipped: only one harness family available — reviewer runs single-agent"
  fi

  # Final footer + verdict: candidates minus the refuter's DROPs, verdict FAIL iff a
  # blocking finding survives — computed, never the reviewer's forgeable verdict line.
  local final; final="$("$script_dir/recompute-footer.sh" "$report" "$refuter_out")"
  { printf '\n## Final footer + verdict (computed)\n'; printf '%s\n' "$final"; } >> "$report"
  printf '%s\n' "$final"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
