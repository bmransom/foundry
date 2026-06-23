---
title: Validation
description: Foundry's verification gates — command, what each catches, when it fires.
type: reference
---

<!-- foundry-seed: validation v1 -->

# Validation

A **gate** is a verification command whose recorded PASS is the evaluator for
done-ness — the gate decides, never the author's assertion.

Every gate fires from two triggers: `.githooks/pre-push` (fast feedback; bypass
once with `git push --no-verify`) and CI (`.github/workflows/check-fast.yml`, the
non-bypassable backstop) — the same script both times, so the two can never disagree.

## Gates

| Gate | Command | Catches | Trigger |
|---|---|---|---|
| Quick gate | `scripts/check-fast.sh` | runs all gates below | pre-push + CI |
| Plugin validate | `claude plugin validate plugins/foundry` (and the marketplace root) | manifest errors | inside the quick gate |
| Byte identity | `scripts/check-byte-identity.sh` | foundry's own copies drifting from `plugins/foundry/templates/verbatim/` | inside the quick gate |
| Knowledge | `python3 scripts/knowledge.py check` + `python3 scripts/test_knowledge.py` | missing or invalid frontmatter; stale `index.md`; knowledge.py regressions | inside the quick gate |
| Script tests | `bash tests/*_test.sh` | script and template behavior regressions | inside the quick gate |
| Context budget | `scripts/check-context-budget.sh` | plugin-resident prose exceeding its line budget | inside the quick gate |
| Harness management fixture | `bash tests/harness_management_test.sh` | missing `harness-status.py` invocation; manifest mutation during verify; unsafe harness shim add/remove | inside the quick gate |
| Harness deliberation live smoke (opt-in) | `python3 plugins/foundry/scripts/harness-deliberation-broker.py live-smoke --repo . --session live-smoke-20260619b --timeout-s 300 --claude-budget-usd 0.25` | real Codex + Claude Code turn protocol; last run PASS recorded both `final.md` payloads and left the worktree unchanged | manual opt-in |
| Site build | `npm ci && npm run build` under `knowledge/` | broken site rendering | CI only |
| Bootstrap eval (L2) | `evals/harness/bootstrap-eval.sh <fixture or all>` | a broken bootstrap; a vacuous generated gate; template regressions in consumer repos | manual + CI dispatch |
| Update eval (L2) | `evals/harness/update-eval.sh <bootstrapped-tree>` | broken refresh; customization overwrites; seed writes | manual |
| Reviewer eval (L3) | `evals/harness/reviewer-eval.sh [N]` | spec-reviewer missing seeded violations or flagging decoys (precision/recall) | manual; required green for a version bump |
| Code-review eval (L3) | `evals/harness/code-review-eval.sh [N]` | code-review missing seeded defects or flagging decoys; the cross-model refuter dropping a real defect (the A/B gates refuter enablement) | manual; required green for a version bump |
| Lifecycle eval (L3) | `evals/harness/lifecycle-eval.sh <bootstrapped-tree>` | the code skill skipping a stage artifact (spec, feature-file-first, pasted PASS, board card) | manual; required green for a version bump |
| Spec-convergence eval (L3) | `SPEC_CONVERGENCE_DRIVER=<loop> evals/harness/spec-convergence-eval.sh` | the convergence loop reporting `SPEC_REVIEW: CLEAN` while a seeded house-style defect remains (fake-clean), caught by an independent grep oracle | manual; required green for a version bump |
