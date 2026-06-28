#!/usr/bin/env bash
# Discriminating eval for the spec-convergence loop.
#
# Proves the loop reports CLEAN only when the seeded house-style defect is ACTUALLY
# gone. The oracle is an INDEPENDENT grep of the final spec for the defect signature
# — it never asks spec-review whether the spec is clean (that would be circular
# self-verification). Fails on fake-clean (verdict CLEAN, defect remains) and on
# not-converged (cap/FINDINGS without removal).
#
# L3: the real run sets SPEC_CONVERGENCE_DRIVER to the actual convergence loop (the
# PostToolUse hook + spec-review + the agent applying fixes). The discrimination is
# exercised deterministically by tests/spec_convergence_eval_test.sh.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fixture="${1:-$HERE/../fixtures/spec-convergence/design.md}"
signature="${SPEC_CONVERGENCE_SIGNATURE:-SEEDED-DEFECT-CONTRADICT}"
driver="${SPEC_CONVERGENCE_DRIVER:?set SPEC_CONVERGENCE_DRIVER to the convergence-loop driver}"

[ -f "$fixture" ] || { echo "spec-convergence-eval: FAIL — missing fixture $fixture"; exit 1; }

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cp "$fixture" "$work/design.md"

# The driver runs the loop on the working spec (review -> apply -> re-review),
# editing the file in place, and prints its final verdict line on stdout.
verdict="$("$driver" "$work/design.md" 2>&1 \
  | grep -E '^SPEC_REVIEW: (CLEAN|FINDINGS)$|CAP REACHED' | tail -1 || true)"

# Independent oracle: did the defect actually leave the spec?
if grep -q "$signature" "$work/design.md"; then
  if [ "$verdict" = "SPEC_REVIEW: CLEAN" ]; then
    echo "spec-convergence-eval: FAIL — fake-clean (verdict CLEAN but '$signature' still in the spec)"
    exit 1
  fi
  echo "spec-convergence-eval: FAIL — not converged ('$signature' remains; verdict: ${verdict:-none})"
  exit 1
fi

[ "$verdict" = "SPEC_REVIEW: CLEAN" ] || {
  echo "spec-convergence-eval: FAIL — defect removed but no CLEAN verdict (got: ${verdict:-none})"
  exit 1
}

echo "spec-convergence-eval: PASS"
