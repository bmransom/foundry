#!/usr/bin/env bash
# Headless bootstrap eval (Layer 2): bootstrap each fixture into a scratch
# repo, then grade by harness-owned invariants plus gate discrimination —
# never a generated gate's green-ness alone (AC-5.2, AC-5.4).
#
# Usage:
#   evals/harness/bootstrap-eval.sh [--keep] <fixture|all>
#   evals/harness/bootstrap-eval.sh --grade-only <tree> <expectations.json>
#
# --keep        retain the scratch dir (always retained on FAIL)
# --grade-only  skip the headless claude call; run grade.py on an existing tree
#
# Results: one NDJSON record per case in evals/results/<fixture>-<epoch>.ndjson;
# the full claude transcript and gate output in the matching .log.
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
FIXTURES_DIR="$FOUNDRY_REPO/evals/fixtures"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

KEEP=0
GRADE_ONLY=0
results=""

usage() { sed -n '2,14p' "${BASH_SOURCE[0]}"; exit 2; }

emit() { # case verdict detail — append one NDJSON record (controlled, quote-free strings)
  local fixture="$1" case_name="$2" verdict="$3" detail="$4"
  printf '{"event":"eval_case","fixture":"%s","case":"%s","verdict":"%s","detail":"%s"}\n' \
    "$fixture" "$case_name" "$verdict" "$detail" | tee -a "$results"
}

expectations_field() { # expectations.json field default
  python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get(sys.argv[2], sys.argv[3]))' "$@"
}

run_gate() { # scratch gate log — exit status is the gate's
  local scratch="$1" gate="$2" log="$3"
  (cd "$scratch" && bash "$gate") >>"$log" 2>&1
}

revert_overlay() { # scratch overlay_dir — restore tracked files, delete untracked overlay files
  local scratch="$1" overlay="$2" relative_path
  while IFS= read -r relative_path; do
    relative_path="${relative_path#./}"
    if git -C "$scratch" ls-files --error-unmatch "$relative_path" >/dev/null 2>&1; then
      git -C "$scratch" checkout -- "$relative_path"
    else
      rm -f "$scratch/$relative_path"
    fi
  done < <(cd "$overlay" && find . -type f)
}

run_fixture() {
  local name="$1"
  local fixture_dir="$FIXTURES_DIR/$name"
  [ -d "$fixture_dir" ] || { echo "bootstrap-eval: unknown fixture '$name'" >&2; exit 2; }

  local stamp scratch log gate fixture_failed=0
  stamp="$(date +%s)"
  results="$RESULTS_DIR/$name-$stamp.ndjson"
  log="$RESULTS_DIR/$name-$stamp.log"
  scratch="$(mktemp -d "${TMPDIR:-/tmp}/foundry-eval-$name.XXXXXX")"
  gate="$(expectations_field "$fixture_dir/expectations.json" gate_command scripts/check-fast.sh)"
  echo "bootstrap-eval: fixture=$name scratch=$scratch"
  echo "bootstrap-eval: log=$log"
  echo "bootstrap-eval: results=$results"

  cp -R "$fixture_dir/repo/." "$scratch/"
  git -C "$scratch" init -q -b main
  git -C "$scratch" config user.email "eval@foundry.local"
  git -C "$scratch" config user.name "foundry-eval"
  git -C "$scratch" add .
  git -C "$scratch" commit -qm "chore: fixture baseline"

  local prompt
  prompt="Use the foundry bootstrap skill to install the foundry setup into this repo. Follow it exactly. Canned interview answers follow. Canned go-ahead: yes, commit.

$(cat "$fixture_dir/answers.md")"

  echo "bootstrap-eval: running headless bootstrap (this takes minutes)"
  if (cd "$scratch" && claude -p "$prompt" \
      --plugin-dir "$FOUNDRY_REPO/plugins/foundry" \
      --dangerously-skip-permissions \
      --verbose --output-format stream-json) >"$log" 2>&1; then
    emit "$name" "bootstrap:claude" "pass" "headless bootstrap completed"
  else
    emit "$name" "bootstrap:claude" "fail" "claude -p exited nonzero - see the log"
    fixture_failed=1
  fi

  python3 "$HARNESS/grade.py" "$fixture_dir/expectations.json" "$scratch" --results "$results" \
    || fixture_failed=1

  if run_gate "$scratch" "$gate" "$log"; then
    emit "$name" "gate:clean" "pass" "$gate exited 0 on the bootstrapped tree"
  else
    emit "$name" "gate:clean" "fail" "$gate exited nonzero on the bootstrapped tree - see the log"
    fixture_failed=1
  fi

  local defect_dir defect
  for defect_dir in "$fixture_dir/defects"/*/; do
    [ -d "$defect_dir" ] || continue
    defect="$(basename "$defect_dir")"
    cp -R "$defect_dir." "$scratch/"
    if run_gate "$scratch" "$gate" "$log"; then
      emit "$name" "defect:$defect" "fail" "gate passed despite the seeded defect"
      fixture_failed=1
    else
      emit "$name" "defect:$defect" "pass" "gate failed on the seeded defect"
    fi
    revert_overlay "$scratch" "$defect_dir"
    if run_gate "$scratch" "$gate" "$log"; then
      emit "$name" "defect:$defect:reverted" "pass" "gate green again after revert"
    else
      emit "$name" "defect:$defect:reverted" "fail" "gate still failing after revert - see the log"
      fixture_failed=1
    fi
  done

  if [ "$fixture_failed" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
    rm -rf "$scratch"
  else
    echo "bootstrap-eval: scratch retained at $scratch"
  fi

  if [ "$fixture_failed" -eq 0 ]; then
    echo "bootstrap-eval: PASS $name"
  else
    echo "bootstrap-eval: FAIL $name"
  fi
  return "$fixture_failed"
}

grade_only() {
  local tree="$1" expectations="$2" name
  name="$(expectations_field "$expectations" fixture unknown)"
  results="$RESULTS_DIR/$name-$(date +%s).ndjson"
  echo "bootstrap-eval: grade-only tree=$tree results=$results"
  if python3 "$HARNESS/grade.py" "$expectations" "$tree" --results "$results"; then
    echo "bootstrap-eval: PASS $name"
  else
    echo "bootstrap-eval: FAIL $name"
    return 1
  fi
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep) KEEP=1; shift ;;
    --grade-only) GRADE_ONLY=1; shift ;;
    -h|--help) usage ;;
    *) break ;;
  esac
done

mkdir -p "$RESULTS_DIR"

if [ "$GRADE_ONLY" -eq 1 ]; then
  [ "$#" -eq 2 ] || usage
  grade_only "$1" "$2"
  exit
fi

[ "$#" -eq 1 ] || usage

overall=0
if [ "$1" = "all" ]; then
  for fixture_path in "$FIXTURES_DIR"/*/; do
    run_fixture "$(basename "$fixture_path")" || overall=1
  done
else
  run_fixture "$1" || overall=1
fi
exit "$overall"
