#!/usr/bin/env bash
# Migration eval (Layer 2): build pre-OKF (convention 1) fixtures, run
# /foundry:update headless against each, and grade harness-owned invariants — the
# residue scan is the independent oracle (it shares no code with the migrator).
#
# Usage:
#   migration-eval.sh [--keep] [--prepare-only] [variant ...]
#     variants default to: okf legacy redgate dirty
#     --prepare-only  build fixtures + baselines + self-test the oracle, then exit 0
#                     (no headless run — the cheap plumbing check)
#     --keep          retain scratch dirs (always retained on FAIL)
#
# Plus three harness-driven cases (full run only): discrimination (a seeded
# incomplete migration the oracle must fail), chaining (a synthetic convention-3
# migration → a convention-1 fixture must reach 3), idempotency (re-run = no change).
#
# Results: evals/results/migration-<epoch>.ndjson + matching .log
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
PLUGIN="$FOUNDRY_REPO/plugins/foundry"
BUILDER="$HARNESS/build-migration-fixtures.sh"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

KEEP=0
PREPARE_ONLY=0
KEYSTONE=0
results=""
eval_failed=0

usage() { sed -n '2,18p' "${BASH_SOURCE[0]}"; exit 2; }

emit() { # fixture case verdict detail
  printf '{"event":"eval_case","fixture":"%s","case":"%s","verdict":"%s","detail":"%s"}\n' \
    "$1" "$2" "$3" "$4" | tee -a "$results"
}

git_baseline() { # tree — commit a clean baseline so the migration has something to revert to
  git -C "$1" init -q
  git -C "$1" add -A
  git -C "$1" -c user.name=eval -c user.email=e@e commit -qm baseline
}

# ── the independent oracle: residue of an incomplete migration ────────────────
# Returns nonzero and prints findings if any pre-OKF residue remains. Targets the
# LIVE surfaces for path refs (not knowledge/ concepts, whose prose/changelog may
# legitimately name the old paths) — so it discriminates without false positives.
residue_scan() { # tree -> findings on stdout, nonzero if any
  local tree="$1" findings=""
  local kindhits
  kindhits="$(grep -rl '^kind:' "$tree" --include='*.md' 2>/dev/null | grep -v node_modules || true)"
  [ -n "$kindhits" ] && findings="${findings}kind: frontmatter remains: ${kindhits//$'\n'/ }; "
  { [ -e "$tree/scripts/docs.py" ] || [ -e "$tree/scripts/test_docs.py" ]; } && findings="${findings}old docs.py/test_docs.py remains; "
  { [ -d "$tree/docs" ] || [ -d "$tree/specs" ]; } && findings="${findings}top-level docs/ or specs/ remains; "
  local surfaces=()
  for s in AGENTS.md .gitignore scripts knowledge/knowledge-config.json .claude/rules .github; do
    [ -e "$tree/$s" ] && surfaces+=("$tree/$s")
  done
  if [ "${#surfaces[@]}" -gt 0 ]; then
    local refhits
    refhits="$(grep -rIn -e 'docs/' -e 'docs\.py' "${surfaces[@]}" 2>/dev/null | grep -v node_modules || true)"
    [ -n "$refhits" ] && findings="${findings}stale docs/ refs in live surfaces; "
  fi
  if [ -n "$findings" ]; then echo "$findings"; return 1; fi
  return 0
}

# ── grade a successfully-migrated tree against harness-owned invariants ────────
grade_migrated() { # fixture tree baseline_gate_rc
  local fixture="$1" tree="$2" baseline_rc="$3"

  # structure
  if [ -d "$tree/knowledge" ] && [ -d "$tree/roadmap/specs" ] && [ ! -d "$tree/docs" ] && [ ! -d "$tree/specs" ]; then
    emit "$fixture" "structure" "pass" "knowledge/ + roadmap/specs/ present; docs/ + specs/ gone"
  else
    emit "$fixture" "structure" "fail" "expected knowledge/ + roadmap/specs/, no docs/ or specs/"; eval_failed=1
  fi

  # independent oracle: no residue
  local residue
  if residue="$(residue_scan "$tree")"; then
    emit "$fixture" "residue-scan" "pass" "no pre-OKF residue"
  else
    emit "$fixture" "residue-scan" "fail" "$residue"; eval_failed=1
  fi

  # knowledge.py check (the migrated, real tool)
  if (cd "$tree" && python3 scripts/knowledge.py check) >/dev/null 2>&1; then
    emit "$fixture" "knowledge-check" "pass" "knowledge.py check exit 0"
  else
    emit "$fixture" "knowledge-check" "fail" "knowledge.py check nonzero"; eval_failed=1
  fi

  # manifest: conventionVersion stamped + sha matches disk
  local conv
  conv="$(python3 -c "import json;print(json.load(open('$tree/.foundry-manifest.json')).get('conventionVersion'))" 2>/dev/null || echo none)"
  if [ "$conv" = "2" ]; then
    emit "$fixture" "manifest-convention" "pass" "conventionVersion=2"
  else
    emit "$fixture" "manifest-convention" "fail" "conventionVersion=$conv (expected 2)"; eval_failed=1
  fi
  if (cd "$tree" && python3 - <<'PY'
import json, hashlib, sys
m = json.load(open(".foundry-manifest.json"))
bad = [p for p, e in m["files"].items()
       if hashlib.sha256(open(p, "rb").read()).hexdigest() != e["sha256"]]
sys.exit(1 if bad else 0)
PY
  ); then
    emit "$fixture" "manifest-sha" "pass" "every manifest sha matches disk"
  else
    emit "$fixture" "manifest-sha" "fail" "a manifest sha does not match disk"; eval_failed=1
  fi

  # branch isolation (AC-1.5): the migration leaves a foundry/migrate-* branch for
  # the caller to review and merge — it does not merge itself. The branch persists,
  # so check it directly (no reflog archaeology).
  if git -C "$tree" branch --list 'foundry/migrate-*' | grep -q .; then
    emit "$fixture" "branch" "pass" "migrated on a foundry/migrate-* branch, left for review"
  else
    emit "$fixture" "branch" "fail" "no foundry/migrate-* branch left for review"; eval_failed=1
  fi

  # no-regression: the canonical gate's post state vs baseline
  local post_rc=0
  (cd "$tree" && bash scripts/check-fast.sh) >/dev/null 2>&1 || post_rc=$?
  if [ "$baseline_rc" -ne 0 ]; then
    emit "$fixture" "no-regression" "pass" "gate red before ($baseline_rc) — not blamed on migration (post=$post_rc)"
  elif [ "$post_rc" -eq 0 ]; then
    emit "$fixture" "no-regression" "pass" "gate green before and after"
  else
    emit "$fixture" "no-regression" "fail" "gate regressed: baseline=0 post=$post_rc"; eval_failed=1
  fi
}

run_headless() { # tree plugin_dir prompt log
  (cd "$1" && claude -p "$3" --plugin-dir "$2" --dangerously-skip-permissions \
      --verbose --output-format stream-json) >>"$4" 2>&1
}

# ── arg parsing ──────────────────────────────────────────────────────────────
variants=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1; shift ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    --keystone) KEYSTONE=1; shift ;;
    -h|--help) usage ;;
    *) variants+=("$1"); shift ;;
  esac
done
if [ "${#variants[@]}" -eq 0 ]; then
  if [ "$KEYSTONE" -eq 1 ]; then variants=(okf); else variants=(okf legacy redgate dirty); fi
fi

stamp="$(date +%s)"
mkdir -p "$RESULTS_DIR"
results="$RESULTS_DIR/migration-$stamp.ndjson"
log="$RESULTS_DIR/migration-$stamp.log"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/foundry-migration-eval.XXXXXX")"

echo "migration-eval: scratch=$SCRATCH"
echo "migration-eval: results=$results"

cleanup() {
  if [ "$eval_failed" -eq 0 ] && [ "$KEEP" -eq 0 ]; then rm -rf "$SCRATCH"
  else echo "migration-eval: scratch retained at $SCRATCH"; fi
}
trap cleanup EXIT

# ── prepare-only: build fixtures + baselines + self-test the oracle ───────────
if [ "$PREPARE_ONLY" -eq 1 ]; then
  echo "migration-eval: --prepare-only"
  for v in okf legacy redgate; do
    bash "$BUILDER" "$v" "$SCRATCH/$v" >/dev/null
    git_baseline "$SCRATCH/$v"
    grc=0; (cd "$SCRATCH/$v" && bash scripts/check-fast.sh) >/dev/null 2>&1 || grc=$?
    echo "  built $v (baseline gate rc=$grc)"
  done
  # oracle self-test: the unmigrated base IS residue (kind:, docs.py, docs/) → must fail;
  # a synthetic clean tree → must pass.
  if residue_scan "$SCRATCH/okf" >/dev/null; then
    echo "  ORACLE SELF-TEST FAIL: scan passed an un-migrated tree"; eval_failed=1
  else
    echo "  oracle self-test: flags un-migrated tree (correct)"
  fi
  clean="$SCRATCH/clean"; mkdir -p "$clean/knowledge" "$clean/roadmap/specs" "$clean/scripts"
  printf '%s\n' '---' 'title: G' 'type: reference' '---' > "$clean/knowledge/glossary.md"
  if residue_scan "$clean" >/dev/null; then
    echo "  oracle self-test: passes a clean migrated tree (correct)"
  else
    echo "  ORACLE SELF-TEST FAIL: scan flagged a clean tree"; eval_failed=1
  fi
  [ "$eval_failed" -eq 0 ] && echo "migration-eval: prepare-only OK" || echo "migration-eval: prepare-only FAIL"
  exit "$eval_failed"
fi

# ── full run: per-variant headless migrate + grade ───────────────────────────
PROMPT="Run the foundry update skill (/foundry:update) on this repo, following it exactly. If it asks for a go-ahead to write or commit, the answer is yes; do not merge any branch it creates."
# Dirty case models a user protecting their WIP — no authorization to commit/stash it.
# This is the faithful test of the clean-tree refusal (a blanket 'yes' would let the
# agent clean the tree itself and defeat the gate).
DIRTY_PROMPT="Run the foundry update skill (/foundry:update) on this repo, following it exactly. I have uncommitted work in progress — do NOT commit, stash, amend, or otherwise touch my uncommitted changes under any circumstances. Do not merge any branch it creates."

for v in "${variants[@]}"; do
  tree="$SCRATCH/$v"
  bash "$BUILDER" "${v/dirty/okf}" "$tree" >/dev/null   # dirty reuses the okf base
  git_baseline "$tree"
  baseline_rc=0; (cd "$tree" && bash scripts/check-fast.sh) >/dev/null 2>&1 || baseline_rc=$?
  if [ "$v" = "dirty" ]; then
    echo "uncommitted change" >> "$tree/docs/glossary.md"   # leave the tree dirty
  fi

  echo "migration-eval: running headless migrate on '$v' (minutes)"
  case_prompt="$PROMPT"; [ "$v" = "dirty" ] && case_prompt="$DIRTY_PROMPT"
  if run_headless "$tree" "$PLUGIN" "$case_prompt" "$log"; then :; else
    emit "$v" "headless" "fail" "claude -p exited nonzero — see the log"; eval_failed=1
  fi

  if [ "$v" = "dirty" ]; then
    # true refusal: docs/ still present, no migrate branch, and the WIP untouched —
    # still exactly one commit (the agent neither migrated nor committed the WIP).
    commits="$(git -C "$tree" rev-list --count HEAD 2>/dev/null || echo 0)"
    if [ -d "$tree/docs" ] && ! git -C "$tree" branch | grep -q 'foundry/migrate' && [ "$commits" = "1" ]; then
      emit "$v" "dirty-refusal" "pass" "refused cleanly — no migration, no branch, WIP untouched"
    else
      emit "$v" "dirty-refusal" "fail" "did not refuse cleanly (branch or extra commit; commits=$commits)"; eval_failed=1
    fi
  else
    grade_migrated "$v" "$tree" "$baseline_rc"
  fi
done

# ── discrimination: the oracle must catch a botched migration ─────────────────
echo "migration-eval: discrimination"
bad="$SCRATCH/discrim"
bash "$BUILDER" okf "$bad" >/dev/null
# simulate a near-complete migration that left one kind: and one stale docs/ ref
mkdir -p "$bad/knowledge"; mv "$bad/docs/glossary.md" "$bad/knowledge/glossary.md"   # still kind:
if residue_scan "$bad" >/dev/null; then
  emit "discrimination" "oracle-catches-residue" "fail" "scan passed a tree with leftover kind:/docs"; eval_failed=1
else
  emit "discrimination" "oracle-catches-residue" "pass" "scan failed the botched migration (correct)"
fi

# ── keystone stops here (skip the extra headless cases) ──────────────────────
if [ "$KEYSTONE" -eq 1 ]; then
  if [ "$eval_failed" -eq 0 ]; then echo "migration-eval: keystone PASS"; else echo "migration-eval: keystone FAIL"; fi
  exit "$eval_failed"
fi

# ── chaining: synthetic convention-3 migration → fixture must reach 3 ──────────
echo "migration-eval: chaining (synthetic convention 3)"
vnext="$SCRATCH/plugin-v3"
cp -R "$PLUGIN" "$vnext"
mkdir -p "$vnext/skills/update/references/migrations"
cat >> "$vnext/skills/update/references/migrations/README.md" <<'EOF'
| 3 | `synthetic-noop` | adds a `.convention3` marker file | a repo without `.convention3` | synthetic-noop.md |
EOF
cat > "$vnext/skills/update/references/migrations/synthetic-noop.md" <<'EOF'
# Migration: synthetic-noop (convention 2 → 3)
Detect: no `.convention3` file at repo root. Transform: create `.convention3`
(empty). Self-verify: the file exists. (Eval-only; proves the chain sequences.)
EOF
chain="$SCRATCH/chain"
bash "$BUILDER" okf "$chain" >/dev/null
git_baseline "$chain"
echo "migration-eval: running headless 2-hop chain (minutes)"
run_headless "$chain" "$vnext" "$PROMPT" "$log" || true
chain_conv="$(python3 -c "import json;print(json.load(open('$chain/.foundry-manifest.json')).get('conventionVersion'))" 2>/dev/null || echo none)"
if [ "$chain_conv" = "3" ] && [ -f "$chain/.convention3" ] && [ -d "$chain/knowledge" ]; then
  emit "chaining" "two-hop" "pass" "convention-1 fixture reached 3 (both migrations applied)"
else
  emit "chaining" "two-hop" "fail" "conventionVersion=$chain_conv, .convention3 $( [ -f "$chain/.convention3" ] && echo yes || echo no)"; eval_failed=1
fi

# ── idempotency: re-run update on a migrated tree → no change ─────────────────
echo "migration-eval: idempotency (re-run)"
if [ -d "$SCRATCH/okf/knowledge" ]; then
  before="$(git -C "$SCRATCH/okf" rev-parse HEAD 2>/dev/null || echo none)"
  run_headless "$SCRATCH/okf" "$PLUGIN" "Use the foundry update skill, follow it exactly. Canned go-ahead: yes." "$log" || true
  after="$(git -C "$SCRATCH/okf" rev-parse HEAD 2>/dev/null || echo none)"
  if residue_scan "$SCRATCH/okf" >/dev/null && [ -d "$SCRATCH/okf/knowledge" ] && [ ! -d "$SCRATCH/okf/docs" ]; then
    emit "idempotency" "rerun-noop" "pass" "re-run left the migrated tree clean (no residue, no re-trigger)"
  else
    emit "idempotency" "rerun-noop" "fail" "re-run disturbed the migrated tree"; eval_failed=1
  fi
fi

# ── summary ──────────────────────────────────────────────────────────────────
if [ "$eval_failed" -eq 0 ]; then echo "migration-eval: PASS"; else echo "migration-eval: FAIL"; fi
exit "$eval_failed"
