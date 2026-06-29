#!/usr/bin/env bash
# verify-finding.sh — make a code-review finding PROVEN, not merely plausible, by RUNNING
# its check instead of re-reading the diff. Two subcommands:
#
#   run <test|snippet|native> <target> [check]   -> one label: verified | refuted | unrunnable
#       The <check> is a REPRO command and follows one contract: exit 0 = the finding
#       REPRODUCES (bug confirmed -> verified); exit 1 = it does NOT reproduce (-> refuted);
#       any other exit / no runnable check -> unrunnable. `native` routes to the `debug`
#       skill (lldb: build with symbols, breakpoint, reproduce); its live run is deferred.
#
#   decide <blocking|advisory> <yes|no:executable> <label|-> <yes|no:execution-active>
#       -> one action: block | advisory | drop
#       Encodes the verify-by-execution rule. The feature is ADDITIVE: with execution off
#       (single-harness) or a non-executable claim, the action is today's read-based behavior
#       (no demotion); demotion fires only when execution is active AND the executable claim
#       could not be reproduced.
#
# Test seam: VERIFY_EXEC_CMD <kind> <target>  stubs the executor (no real build/run/lldb),
# its exit code feeding the same 0/1/other -> verified/refuted/unrunnable mapping.
set -euo pipefail

run() {
  kind="${1:?usage: verify-finding.sh run <test|snippet|native> <target> [check]}"
  target="${2:-}"
  check="${3:-}"
  if [ -n "${VERIFY_EXEC_CMD:-}" ]; then
    set +e; "$VERIFY_EXEC_CMD" "$kind" "$target" >/dev/null 2>&1; rc=$?; set -e
  else
    case "$kind" in
      test|snippet|native)
        # All three run a repro command (exit 0 = the finding reproduces). `native` is an
        # lldb-driven repro the `debug` skill builds (build -g, breakpoint, run); a finding
        # with no runnable repro stays unrunnable. Subshell so a check using the `exit`
        # builtin cannot escape the rc capture.
        if [ -z "$check" ]; then rc=2; else
          set +e; ( eval "$check" ) >/dev/null 2>&1; rc=$?; set -e
        fi ;;
      *) rc=2 ;;
    esac
  fi
  case "$rc" in
    0) echo verified ;;
    1) echo refuted ;;
    *) echo unrunnable ;;
  esac
}

decide() {
  severity="${1:?usage: verify-finding.sh decide <blocking|advisory> <yes|no> <label|-> <yes|no>}"
  executable="${2:?executable yes|no}"
  label="${3:-}"
  active="${4:?execution-active yes|no}"

  # A blocking finding keeps blocking unless execution actively refutes/can't-prove it.
  block_if_blocking() { [ "$severity" = blocking ] && echo block || echo advisory; }

  # AC-1.4: a non-executable claim keeps its read-based verification (unchanged).
  # AC-1.5: execution off (single-harness) -> no-op, today's behavior (no demotion).
  if [ "$executable" = no ] || [ "$active" = no ]; then
    block_if_blocking; return 0
  fi

  # Execution active AND the claim is executable -> honor the label.
  case "$label" in
    verified)            block_if_blocking ;;          # AC-1.1: may block
    refuted)             echo drop ;;                   # AC-1.2: ran and disproved
    *)                   echo advisory ;;               # AC-1.3: unrunnable/hypothesis -> demote
  esac
}

cmd="${1:?usage: verify-finding.sh run|decide ...}"; shift
case "$cmd" in
  run)    run "$@" ;;
  decide) decide "$@" ;;
  *) echo "verify-finding.sh: unknown subcommand '$cmd'" >&2; exit 2 ;;
esac
