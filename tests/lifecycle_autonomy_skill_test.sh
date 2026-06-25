#!/usr/bin/env bash
# Static test for the code skill's autonomy dial. The dial's detail lives in
# references/autonomy.md (SKILL.md is context-budgeted); assert the reference encodes the
# contract and the skill points to it. Hermetic — greps text, runs nothing.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL="$REPO/plugins/foundry/skills/code/SKILL.md"
REF="$REPO/plugins/foundry/skills/code/references/autonomy.md"
fail() { echo "FAIL: $1" >&2; exit 1; }

[ -f "$REF" ] || fail "missing references/autonomy.md"
ref() { grep -qi "$1" "$REF" || fail "autonomy.md must $2"; }

# The three levels.
for level in Supervised Guided Autonomous; do ref "$level" "name the $level level"; done
# The stop-point kinds.
for kind in feature card epic roadmap; do ref "$kind" "name the $kind stop-point kind"; done
# The dividing axis: a soft fork (level decides) vs a hard blocker (halts all).
ref "soft fork" "define the soft fork"
ref "hard blocker" "define the hard blocker"
# The invariant safety floor.
grep -qi "never push or merge to the default branch" "$REF" \
  || fail "autonomy.md must state the never-push/merge-to-default invariant"
# Run-state persistence: path + schema fields.
grep -q "\.foundry/tmp/lifecycle-run\.json" "$REF" || fail "autonomy.md must name the run-state path"
for field in level stopPoint completed; do
  grep -q "$field" "$REF" || fail "autonomy.md must document the run-state field $field"
done
# Directive read once, never re-asked.
grep -qi "re-ask" "$REF" || fail "autonomy.md must state the directive is read once, never re-asked"
# Harness integration + the Codex approval-mode mapping.
ref "/loop" "cover the /loop harness"
ref "/goal" "cover the Codex /goal harness"
grep -q "Read-only" "$REF" || fail "autonomy.md must map the Codex Read-only mode"
grep -q "Full Access" "$REF" || fail "autonomy.md must map the Codex Full Access mode"

# The skill links the reference and flags the dial at Frame + Finish.
grep -q "references/autonomy.md" "$SKILL" || fail "code/SKILL.md must link references/autonomy.md"
grep -qi "autonomy dial" "$SKILL" || fail "code/SKILL.md must flag the autonomy dial"

echo "lifecycle_autonomy_skill_test: PASS"
