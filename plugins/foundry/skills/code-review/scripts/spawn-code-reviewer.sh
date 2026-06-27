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
  echo "usage: spawn-code-reviewer.sh [--dry-run] [--print-harness] [--skip-permissions] [--harness <family>] [--base <ref>] [--review-cap <n>] [--consecutive-clean <n>] <spec-dir> [project-dir]" >&2
}

# Spawn one fresh-context session (role = reviewer|refuter) that writes its artifact
# to $out. CODE_REVIEW_SPAWN_CMD is a test-only seam: a stub that writes $out in place
# of the real detached spawn. Production pipes the prompt to the shared runner. Relies
# on main()'s locals (runner, runner_args, refuter_family, dir) via dynamic scope.
spawn_session() {
  local role="$1" out="$2" prompt="$3"
  if [ -n "${CODE_REVIEW_SPAWN_CMD:-}" ]; then
    "$CODE_REVIEW_SPAWN_CMD" "$role" "$out"
    return
  fi
  if [ "$role" = refuter ]; then
    printf '%s\n' "$prompt" | AGENT_HARNESS="$refuter_family" "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review-refuter "$dir"
  else
    printf '%s\n' "$prompt" | "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review "$dir"
  fi
}

# Build the reviewer prompt for a report path (uses main's spec_dir/range via dynamic
# scope). Each inner-loop pass gets its own report path as $1.
reviewer_prompt() {
  printf '%s' "Use the code-review skill at $(plugin_root)/skills/code-review/SKILL.md to review the change for spec $spec_dir in fresh context. This is READ-ONLY: do not edit any file. Diff range: $range. Read the spec files, the diff, roadmap/ROADMAP.md, knowledge/validation.md, and knowledge/glossary.md; run python3 scripts/knowledge.py check yourself. Grade every dimension from artifacts you read or commands you run, never from the author's claims. End the report with the findings body, then the FLAGGED: footer (one line per BLOCKING finding), then a single final line CODE_REVIEW: PASS or CODE_REVIEW: FAIL. Write the complete report to the absolute path $1."
}

main() {
  local script_dir; script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local runner; runner="$(plugin_root)/scripts/spawn-fresh-session.sh"
  local dry_run=0 skip=0 single_pass=0 base="" harness_flag="" review_cap_flag="" consecutive_flag="" runner_args=()
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1; runner_args+=("$1"); shift ;;
      --print-harness) exec "$runner" --print-harness ;;
      --skip-permissions|--yolo) skip=1; runner_args+=("$1"); shift ;;
      --single-pass) single_pass=1; shift ;;
      --harness)
        [ "$#" -ge 2 ] || { usage; exit 2; }
        harness_flag="$2"; shift 2 ;;
      --review-cap)
        [ "$#" -ge 2 ] || { usage; exit 2; }
        review_cap_flag="$2"; shift 2 ;;
      --consecutive-clean)
        [ "$#" -ge 2 ] || { usage; exit 2; }
        consecutive_flag="$2"; shift 2 ;;
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

  # Diff base: --base overrides; the default is the shared resolver
  # (origin/HEAD -> main -> HEAD), so the code-review range matches the rest of
  # foundry. Review the working diff if none resolves.
  if [ -z "$base" ]; then
    base="$("$runner" --resolve-base "$dir" 2>/dev/null || true)"
  fi
  local range
  if [ -n "$base" ]; then range="$base..HEAD"; else range="(no base resolved — review the working diff)"; fi

  local review_dir=".foundry/reports/code-review"
  # Absolute report path under the PRIMARY tree, so retiring a spawned worktree
  # cannot delete the report (the harness cwd is the worktree after isolation).
  # The -$$ (pid) suffix avoids a same-second collision when parallel agents review (CR-4).
  local report="$dir/$review_dir/$(date +%Y%m%d%H%M%S)-$$-code-review.md"

  # The reviewer prompt is built per pass by reviewer_prompt() — each inner-loop pass
  # writes its own report path.

  # Harness detection has one source: the shared runner (CODE_REVIEW_REVIEWER_FAMILY
  # overrides it for deterministic tests).
  local reviewer_family
  reviewer_family="${CODE_REVIEW_REVIEWER_FAMILY:-$("$runner" --print-harness)}"
  # The refuter's family: --harness overrides; otherwise derive it from the manifest's
  # harnesses via refuter-family.sh — never a hardcoded list or env var (AC-13.1). An
  # empty result (single-family repo, or no manifest) skips the refuter (single-agent).
  local refuter_family=""
  if [ -n "$harness_flag" ]; then
    refuter_family="$harness_flag"
  elif [ -f "$dir/.foundry/manifest.json" ]; then
    refuter_family="$("$script_dir/refuter-family.sh" "$reviewer_family" "$dir/.foundry/manifest.json" 2>/dev/null || echo none)"
    [ "$refuter_family" = none ] && refuter_family=""
  fi
  local refuter_on=0
  if [ -n "$refuter_family" ] && [ "$refuter_family" != "$reviewer_family" ]; then refuter_on=1; fi

  local refuter_head="Use the code-review skill's REFUTER contract at $(plugin_root)/skills/code-review/SKILL.md. You are a single asymmetric refute pass — NOT a debate. READ-ONLY: edit nothing. You receive ONLY the candidate FLAGGED findings and the diff for range $range; you do NOT see the reviewer's reasoning. Per candidate finding, KEEP it only with concrete evidence it is real, else mark it DROP. You may only REMOVE a finding, never ADD one."

  # --- Dry run: preview every launch, spawn nothing, wait for nothing. --------
  if [ "$dry_run" -eq 1 ]; then
    echo "code-review launch: harness=$reviewer_family spec-dir=$spec_dir range=$range"
    echo "report: $report"
    printf '%s\n' "$(reviewer_prompt "$report")" | "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review "$dir"
    echo "report: $report"
    if [ "$refuter_on" -eq 1 ]; then
      echo "refuter: spawn on harness family $refuter_family (read-only, candidate findings + diff only)"
      printf '%s\n' "$refuter_head Output one line per candidate finding (KEEP <signature> or DROP <signature>), then a final line REFUTER: DONE." \
        | AGENT_HARNESS="$refuter_family" "$runner" ${runner_args[@]+"${runner_args[@]}"} --name code-review-refuter "$dir"
      echo "refuter: previewed on harness family $refuter_family; final footer = candidates minus DROPs"
    else
      echo "refuter skipped: no complementary harness family — reviewer runs single-agent"
    fi
    return 0
  fi

  # --- Real run: inner review-convergence loop (default; --single-pass = one pass) --
  local wait_timeout="${CODE_REVIEW_WAIT_TIMEOUT:-300}" wait_poll="${CODE_REVIEW_WAIT_POLL:-1}"
  # Precedence: flag > test-env > named default (AC-13.2, AC-13.4).
  local review_cap="${review_cap_flag:-${CODE_REVIEW_REVIEW_CAP:-20}}"   # 20-pass ceiling (AC-12.1)
  local consecutive_target="${consecutive_flag:-2}"   # stop after two consecutive no-new passes
  local max_passes="$review_cap"; [ "$single_pass" -eq 1 ] && max_passes=1
  mkdir -p "$dir/$review_dir"

  # Re-review in fresh context each pass; union findings (one normalized key) until two
  # consecutive passes add nothing new, or the cap. Immutable inputs (range, prompt, the
  # docs-sync/glossary/size scans the reviewer runs) are not re-derived by the runner —
  # only the re-spawn + union recur per pass.
  local union_file="$report.union"; : > "$union_file"
  local prev_count=-1 no_new=0 pass=0 count
  while [ "$pass" -lt "$max_passes" ]; do
    pass=$((pass + 1))
    local pass_report="$report.pass$pass"
    spawn_session reviewer "$pass_report" "$(reviewer_prompt "$pass_report")"
    if ! "$script_dir/wait-for-report.sh" "$pass_report" "$wait_timeout" "$wait_poll"; then
      echo "code-review: reviewer report (pass $pass) did not complete within ${wait_timeout}s — FAIL (not converged)" >&2
      exit 1
    fi
    "$script_dir/footer-algebra.sh" union "$union_file" "$pass_report" > "$union_file.next"
    mv "$union_file.next" "$union_file"
    count="$(grep -c '^FLAGGED:' "$union_file" || true)"
    if [ "$count" -eq "$prev_count" ]; then no_new=$((no_new + 1)); else no_new=0; prev_count="$count"; fi
    if [ "$single_pass" -eq 0 ] && [ "$no_new" -ge "$consecutive_target" ]; then break; fi
  done
  echo "report: $report (converged after $pass pass(es))"

  # Cross-model refuter: ONE pass over the converged union (footer + diff only).
  local refuter_out=/dev/null
  if [ "$refuter_on" -eq 1 ]; then
    local footer_payload; footer_payload="$(cat "$union_file")"
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

  # Final footer + verdict: the union minus the refuter's DROPs, verdict FAIL iff a
  # blocking finding survives — computed, never the reviewer's forgeable verdict line.
  local final; final="$("$script_dir/recompute-footer.sh" "$union_file" "$refuter_out")"
  # Detail = the final pass's findings PROSE (its own FLAGGED footer + forgeable verdict
  # stripped). The authoritative signatures + verdict are the COMPUTED footer below — the
  # union across passes minus the refuter's DROPs — so a dropped finding never leaks into
  # the actionable output, while the evidence/problem/fix the contract requires is kept.
  { printf '# Code review — converged after %s pass(es)\n\n## Findings (detail)\n\n' "$pass"
    grep -vE '^FLAGGED:|^CODE_REVIEW:' "$report.pass$pass" || true
    printf '\n## Final footer + verdict (computed: union across passes minus refuter DROPs)\n'
    printf '%s\n' "$final"
  } > "$report"
  cat "$report"
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
