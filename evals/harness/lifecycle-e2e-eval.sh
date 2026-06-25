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

mode=run   # run | plan | setup | verify | bootstrap | feature
dry=0
FEATURE=""
harnesses="claude-code codex"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --plan) mode=plan; shift ;;
    --setup-only) mode=setup; shift ;;     # deterministic: fresh repo + verbatim install + verify
    --verify-only) mode=verify; shift ;;   # deterministic: verify an existing install (LIFECYCLE_E2E_SETUP_DIR)
    --bootstrap) mode=bootstrap; shift ;;  # headless slice: fresh repo + drive the bootstrap skill, then verify
    --feature)                             # headless slice: drive ONE feature through the lifecycle in a bootstrapped repo
      [ "$#" -ge 2 ] || { echo "lifecycle-e2e: --feature needs a name" >&2; exit 2; }
      mode=feature; FEATURE="$2"; shift 2 ;;
    --dry-run) dry=1; shift ;;             # with --bootstrap/--feature: print the headless command + prompt, run nothing
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

# --- Headless drive (the heavy part) -------------------------------------------
# The canned bootstrap prompt points the agent at THIS repo's local bootstrap skill
# (not the cached release), so the dogfood tests the local foundry. Mirrors how
# code-review-eval.sh references the skill by path.
bootstrap_prompt() {
  local plugin_root="$REPO/plugins/foundry"
  cat <<PROMPT
Read and follow the foundry bootstrap skill at $plugin_root/skills/bootstrap/SKILL.md, plus its references/generate.md and references/verify.md. The plugin root is $plugin_root; its templates live at $plugin_root/templates/ (verbatim/ and seeds/). Bootstrap the foundry setup into the CURRENT directory, a fresh empty git repo.

This is a headless run with CANNED interview answers — do NOT ask questions, use these verbatim:
- Target harness(es): both (claude-code and codex).
- Project: a Texas Hold'em poker engine with a backend HTTP API, computer players, and a minimal browser UI for a human to play turn-based hands.
- Domain terms: hand, hole cards, community cards, board, pot, side pot, blind, betting round (preflop/flop/turn/river), action (fold/check/call/bet/raise), showdown. Debt terms: "card value" -> rank; "AI" -> CPU player.
- Vocabulary polarity: embrace the domain (a product).
- API surface: yes — an HTTP API the future browser UI will use.
- Gate commands: the stack's test + lint + build. Pick ONE sensible stack for a poker engine + HTTP API + browser UI (e.g. Python or TypeScript) and wire scripts/check-fast.sh to that stack's real test/lint/build.
- Parallel agents: yes.
- Unit of work for logging: a hand.
- First epic: "Playable Texas Hold'em vs computer players."

Complete all five phases (Inspect, Interview, Copy, Generate, Verify). In Verify, run scripts/check-fast.sh and paste its output, and seed-then-remove a failing check to prove the gate discriminates. Do NOT commit — leave the working tree in place for collection (skip the final commit/ask step).
PROMPT
}

drive_stage() {           # $1 repo  $2 prompt  $3 log  -> headless agent exit code
  local repo="$1" prompt="$2" log="$3"
  # The headless agent's non-interactive tool shells don't source the login profile, so a
  # version-manager `node` runtime is off PATH; the agent then hits "command not found" on
  # node and every node-shebang tool (tsc/vitest/cucumber) until it recovers. Resolve node
  # here — where the gate runs green — and prepend its dir to the PATH claude -p inherits,
  # so the agent's shells find the toolchain from the first call.
  local toolbin=""; command -v node >/dev/null 2>&1 && toolbin="$(dirname "$(command -v node)")"
  ( cd "$repo" && PATH="${toolbin:+$toolbin:}$PATH" timeout "${LIFECYCLE_E2E_STAGE_TIMEOUT:-1800}" \
      claude -p "$prompt" --dangerously-skip-permissions --verbose --output-format stream-json ) >"$log" 2>&1
}

feat_desc() {             # $1 = roadmap feature -> one-line description for the prompt
  case "$1" in
    deck-and-cards)    echo "a Deck and Card domain model — a 52-card deck (4 suits x 13 ranks), shuffle, and deal N cards; the engine foundation betting and hand-evaluation build on." ;;
    hand-evaluation)   echo "evaluate the best five-card hand from seven cards (hole + board) and rank two hands against each other." ;;
    betting-rounds)    echo "the betting action state machine (fold/check/call/bet/raise) across preflop, flop, turn, and river." ;;
    pot-and-side-pots) echo "pot accounting, including correct side pots when players are all-in for different amounts." ;;
    cpu-player)        echo "a computer player that picks a legal action from the current betting state." ;;
    turn-based-loop)   echo "the hand loop: deal -> betting round -> advance the street -> showdown -> award the pot." ;;
    sim-runner)        echo "a 'sim --hands N' command that plays CPU-vs-CPU hands and reports the outcome." ;;
    http-api)          echo "an HTTP API serving game state and accepting actions (start hand, act, advance)." ;;
    web-ui)            echo "a minimal browser client to play one hand against the CPU players over the HTTP API." ;;
    *)                 echo "the $1 feature." ;;
  esac
}

feature_prompt() {        # $1 = feature, $2 = description -> the headless lifecycle prompt
  local plugin_root="$REPO/plugins/foundry"
  cat <<PROMPT
Read and follow the foundry code skill at $plugin_root/skills/code/SKILL.md to implement ONE feature in this already-bootstrapped foundry repo (the current directory). The sub-skills it names (spec-review, code-review, naming-standards, design-patterns, modular-structure, performance) are available — use them as the code skill directs.

Feature: $1 — $2

Drive every lifecycle stage in order:
- Frame: a new feature (all stages).
- Spec: write roadmap/specs/$1/{requirements,design,tasks}.md in the repo's spec format and the knowledge/glossary.md vocabulary; run spec-review to convergence.
- Plan: bite-sized TDD tasks in tasks.md; claim the board card in roadmap/ROADMAP.md.
- Build: the features/ Scenario FIRST, then TDD red->green; respect the glossary and AGENTS.md Boundaries (the engine lives in src/domain/); stage explicit paths.
- Verify: run scripts/check-fast.sh and paste the PASS line.
- Knowledge: python3 scripts/knowledge.py check; log touched concepts.
- Review: run code-review in fresh context; fix every blocking finding.

Commit your work on a feature branch (the code skill branches first off the default branch) so code-review has a real diff to review; do NOT push and do NOT merge to the default branch — leave the branch in place for collection. Move the board card to Validating.
PROMPT
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
  bootstrap)
    repo="${LIFECYCLE_E2E_SETUP_DIR:-$(mktemp -d)}"
    out="$RESULTS/lifecycle-e2e-bootstrap-$$"
    mkdir -p "$out"
    log="$out/bootstrap.log"
    prompt="$(bootstrap_prompt)"
    if [ "$dry" -eq 1 ]; then
      echo "lifecycle-e2e bootstrap — DRY RUN (nothing run)"
      echo "fresh repo: $repo"
      echo "results:    $out"
      echo "command:    (cd \$repo && claude -p <prompt> --dangerously-skip-permissions --verbose --output-format stream-json) > $log"
      echo "--- canned bootstrap prompt (local plugin, not the cached release) ---"
      printf '%s\n' "$prompt"
      exit 0
    fi
    fresh_repo "$repo"
    echo "lifecycle-e2e bootstrap: headless claude bootstrapping foundry in $repo"
    echo "  log: $log"
    drive_stage "$repo" "$prompt" "$log" || echo "bootstrap: headless agent exited nonzero (see $log)" >&2
    echo "=== bootstrap artifacts ==="
    for f in AGENTS.md CLAUDE.md .foundry/manifest.json roadmap/ROADMAP.md knowledge/glossary.md scripts/check-fast.sh features; do
      [ -e "$repo/$f" ] && echo "PRESENT $f" || echo "MISSING $f"
    done
    if verify_install "$repo"; then echo "verbatim byte-identity: PASS"; else echo "verbatim byte-identity: FAIL (friction)"; fi
    echo "=== generated check-fast ==="
    if ( cd "$repo" && bash scripts/check-fast.sh ) >"$out/check-fast.log" 2>&1; then
      echo "generated check-fast: PASS"
    else
      echo "generated check-fast: FAIL — see $out/check-fast.log (workflow friction)"
    fi
    # Regression signal for the generate.md vocab-lint fix: a generated lint must scope
    # to markdown prose, else it false-matches a debt term in a lockfile/generated tree.
    if [ -f "$repo/scripts/vocab-lint.sh" ]; then
      if grep -q '\.md' "$repo/scripts/vocab-lint.sh"; then
        echo "vocab-lint scoping: PASS (restricts to markdown prose)"
      else
        echo "vocab-lint scoping: FRICTION — generated lint may scan non-prose; see bootstrap generate.md"
      fi
    fi
    cp -R "$repo" "$out/repo" 2>/dev/null || true
    echo "collected: $out/repo"
    exit 0 ;;
  feature)
    feat="${FEATURE:?--feature needs a name}"
    out="$RESULTS/lifecycle-e2e-feature-$feat-$$"
    prompt="$(feature_prompt "$feat" "$(feat_desc "$feat")")"
    if [ "$dry" -eq 1 ]; then
      echo "lifecycle-e2e feature ($feat) — DRY RUN (nothing run)"
      echo "results: $out"
      echo "--- canned feature prompt (local code skill) ---"
      printf '%s\n' "$prompt"
      exit 0
    fi
    repo="${LIFECYCLE_E2E_SETUP_DIR:?--feature needs LIFECYCLE_E2E_SETUP_DIR (a bootstrapped repo)}"
    [ -d "$repo" ] || { echo "lifecycle-e2e: bootstrapped repo $repo not found" >&2; exit 2; }
    mkdir -p "$out"
    log="$out/$feat.log"
    echo "lifecycle-e2e feature: headless claude building '$feat' in $repo"
    echo "  log: $log"
    drive_stage "$repo" "$prompt" "$log" || echo "feature: headless agent exited nonzero (see $log)" >&2
    echo "=== feature artifacts ==="
    [ -d "$repo/roadmap/specs/$feat" ] && echo "PRESENT roadmap/specs/$feat (spec)" || echo "MISSING roadmap/specs/$feat (no spec written)"
    if find "$repo/features" -name '*.feature' -newer "$repo/AGENTS.md" 2>/dev/null | grep -q .; then
      echo "PRESENT new/updated feature Scenario"
    else
      echo "(no new feature Scenario detected since bootstrap)"
    fi
    echo "=== check-fast (still green after the feature?) ==="
    if ( cd "$repo" && bash scripts/check-fast.sh ) >"$out/check-fast.log" 2>&1; then
      echo "check-fast: PASS"
    else
      echo "check-fast: FAIL — see $out/check-fast.log (workflow friction)"
    fi
    cp -R "$repo" "$out/repo" 2>/dev/null || true
    echo "collected: $out/repo"
    exit 0 ;;
esac

# --- Full run: the headless lifecycle drive (built next; heavy, on-demand) ------
# drive_stage()  — invoke the headless agent (claude -p / codex) per stage, canned inputs.
# verify_gate()  — run the generated repo's check-fast; require PASS.
# assert_sim()   — run 'sim --hands N'; assert the acceptance invariants + HTTP smoke.
# collect_artifacts() / report_friction() — gather + grade workflow friction.
echo "lifecycle-e2e: full headless run not yet implemented — install foundation ready (--setup-only)." >&2
echo "Next slice: drive_stage (headless bootstrap with the canned poker answers)." >&2
exit 3
