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

mode=run   # run | plan | setup | verify
harnesses="claude-code codex"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan) mode=plan; shift ;;
    --setup-only) mode=setup; shift ;;     # deterministic: fresh repo + verbatim install + verify
    --verify-only) mode=verify; shift ;;   # deterministic: verify an existing install (LIFECYCLE_E2E_SETUP_DIR)
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

[ "$mode" = plan ] && { print_plan; exit 0; }

# --- Deterministic install (bootstrap's byte-exact Copy phase) -----------------
# fresh_repo + install_foundry + verify_install are the deterministic foundation of a
# run; drive_stage (the headless lifecycle, the heavy part) builds on them next.

fresh_repo() {            # $1 = target dir — a clean, empty git repo
  local repo="$1"
  mkdir -p "$repo"
  git -C "$repo" init -q
}

install_foundry() {       # $1 = target repo — copy foundry's verbatim templates byte-exact
  local repo="$1" templates="$REPO/plugins/foundry/templates/verbatim"
  while IFS= read -r -d '' tf; do
    local rel="${tf#"$templates/"}"
    mkdir -p "$repo/$(dirname "$rel")"
    cp "$tf" "$repo/$rel"
  done < <(find "$templates" -type f -not -path '*/__pycache__/*' -print0)
}

verify_install() {        # $1 = target repo — each verbatim template byte-identical (modulo marker)
  local repo="$1" templates="$REPO/plugins/foundry/templates/verbatim" bad=0
  while IFS= read -r -d '' tf; do
    local rel="${tf#"$templates/"}"
    local copy="$repo/$rel"
    if [ ! -f "$copy" ]; then echo "MISSING $rel" >&2; bad=1; continue; fi
    if ! diff -q <(grep -vF 'foundry-template:' "$tf") <(grep -vF 'foundry-template:' "$copy") >/dev/null; then
      echo "DRIFT $rel" >&2; bad=1
    fi
  done < <(find "$templates" -type f -not -path '*/__pycache__/*' -print0)
  return "$bad"
}

case "$mode" in
  setup)
    repo="${LIFECYCLE_E2E_SETUP_DIR:-$(mktemp -d)}"
    fresh_repo "$repo"
    install_foundry "$repo"
    if verify_install "$repo"; then
      echo "lifecycle-e2e setup: BYTE-IDENTITY PASS — foundry verbatim templates installed; repo=$repo"
      exit 0
    fi
    echo "lifecycle-e2e setup: BYTE-IDENTITY FAIL; repo=$repo" >&2; exit 1 ;;
  verify)
    repo="${LIFECYCLE_E2E_SETUP_DIR:?--verify-only needs LIFECYCLE_E2E_SETUP_DIR}"
    if verify_install "$repo"; then
      echo "lifecycle-e2e verify: BYTE-IDENTITY PASS; repo=$repo"; exit 0
    fi
    echo "lifecycle-e2e verify: BYTE-IDENTITY FAIL; repo=$repo" >&2; exit 1 ;;
esac

# --- Full run: the headless lifecycle drive (built next; heavy, on-demand) ------
# drive_stage()  — invoke the headless agent (claude -p / codex) per stage, canned inputs.
# verify_gate()  — run the generated repo's check-fast; require PASS.
# assert_sim()   — run 'sim --hands N'; assert the acceptance invariants + HTTP smoke.
# collect_artifacts() / report_friction() — gather + grade workflow friction.
echo "lifecycle-e2e: full headless run not yet implemented — install foundation ready (--setup-only)." >&2
echo "Next slice: drive_stage (headless bootstrap with the canned poker answers)." >&2
exit 3
