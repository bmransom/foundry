---
title: Validation
description: Every verification gate — command, what it catches, when it fires.
kind: reference
---

<!-- foundry-seed: validation v1 -->

# Validation

A **gate** is a verification command whose recorded PASS is the evaluator for
done-ness — the gate decides, never the author's assertion.

Every gate fires from two triggers: `.githooks/pre-push` (fast feedback; bypass
once with `git push --no-verify`) and CI (the non-bypassable backstop) — the same
script both times, so the two can never disagree.

## Gates

Add a row for every gate. A heavy gate (long benchmark, full suite) stays manual;
document its command and when to run it.

| Gate | Command | Catches | Trigger |
|---|---|---|---|
| Quick gate | `scripts/check-fast.sh` | lint, unit tests, doc frontmatter | pre-push + CI |
