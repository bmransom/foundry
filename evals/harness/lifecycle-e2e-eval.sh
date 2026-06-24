#!/usr/bin/env bash
# Lifecycle E2E eval (Layer 4): from a FRESH repo, install foundry and drive the
# full code lifecycle via headless agents to build the poker fixture, then assert
# the gates passed and a CPU-vs-CPU hand completes. The signal is WORKFLOW friction
# (where the agent needed a nudge / produced a wrong artifact), surfaced
# app-agnostically. Heavyweight, on-demand — NOT wired into check-fast.
#
# Usage:
#   lifecycle-e2e-eval.sh --plan [--harness claude-code|codex|both]   print the plan; run nothing
#   lifecycle-e2e-eval.sh [--harness claude-code|codex|both]          run it (drives headless agents)
#
# See evals/fixtures/lifecycle-e2e/README.md for the fixture and acceptance.
set -euo pipefail

HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HARNESS_DIR/../.." && pwd)"
FIXTURE="$REPO/evals/fixtures/lifecycle-e2e"
RESULTS="$REPO/evals/results"

plan=0
harnesses="claude-code codex"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan) plan=1; shift ;;
    --harness)
      [ "$#" -ge 2 ] || { echo "lifecycle-e2e: --harness needs a value" >&2; exit 2; }
      case "$2" in both) harnesses="claude-code codex" ;; claude-code|codex) harnesses="$2" ;; *) echo "lifecycle-e2e: unknown harness '$2'" >&2; exit 2 ;; esac
      shift 2 ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "lifecycle-e2e: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

# The code lifecycle stages each feature passes (the code skill's gates).
stages="Frame Spec Plan Build Verify Knowledge Review Finish"
# The poker feature roadmap (the fixture drives each through the lifecycle).
features="deck-and-cards hand-evaluation betting-rounds pot-and-side-pots cpu-player turn-based-loop sim-runner http-api web-ui"

print_plan() {
  echo "lifecycle-e2e — PLAN (nothing run)"
  echo "fixture:        $FIXTURE/README.md"
  echo "harness matrix: $harnesses"
  echo "results dir:    $RESULTS/lifecycle-e2e-<harness>-<stamp>/"
  echo
  echo "per harness:"
  echo "  1. fresh repo      — git init in a temp dir, empty"
  echo "  2. install foundry — bootstrap skill, canned poker interview answers (see README)"
  echo "  3. drive lifecycle — headless agent runs each feature through every stage:"
  for f in $features; do echo "       - $f : $stages"; done
  echo "  4. verify gates    — generated repo 'check-fast' green; each feature's Scenario green; recorded PASS"
  echo "  5. assert app      — 'sim --hands N' invariants + HTTP smoke (one hand via the API); then serve for human browser play"
  echo "  6. collect         — copy generated repo to the results dir for human review"
  echo "  7. workflow report — per stage: unaided | retried | wrong-artifact | stuck  (the eval's signal)"
}

if [ "$plan" -eq 1 ]; then print_plan; exit 0; fi

# --- Run mode: built incrementally over the initial iterations -----------------
# Each helper is the next slice of work; the heavy part is drive_stage (headless).
# fresh_repo()        — mktemp -d; git init; empty tree.
# install_foundry()   — make the plugin available; run bootstrap headless with the
#                       canned answers; assert AGENTS.md + manifest + check-fast exist.
# drive_stage()       — invoke the headless agent (claude -p / codex) for one stage
#                       with the fixture inputs; capture the transcript.
# verify_gate()       — run the generated repo's check-fast; require PASS.
# assert_sim()        — run 'sim --hands N'; assert the acceptance invariants.
# collect_artifacts() — copy the generated repo to the results dir.
# report_friction()   — per stage: unaided | retried | wrong-artifact | stuck.
echo "lifecycle-e2e: run mode is built incrementally — use --plan for the staged plan." >&2
echo "Next slice: fresh_repo + install_foundry (bootstrap headless with the canned poker answers)." >&2
exit 3
