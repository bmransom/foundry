---
title: Validation
description: Foundry's verification gates — command, what each catches, when it fires.
kind: reference
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
| Docs | `python3 scripts/docs.py check` + `python3 scripts/test_docs.py` | missing or invalid frontmatter; docs.py regressions | inside the quick gate |
| Script tests | `bash tests/*_test.sh` | script and template behavior regressions | inside the quick gate |
| Context budget | `scripts/check-context-budget.sh` | plugin-resident prose exceeding its line budget | inside the quick gate |
| Docs build | `npm ci && npm run build` under `docs/` | broken site rendering | CI only |
| Bootstrap eval (L2) | `evals/harness/bootstrap-eval.sh <fixture or all>` | a broken bootstrap; a vacuous generated gate; template regressions in consumer repos | manual + CI dispatch |
| Update eval (L2) | `evals/harness/update-eval.sh <bootstrapped-tree>` | broken refresh; customization overwrites; seed writes | manual |
