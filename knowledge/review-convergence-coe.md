---
title: COE — spec-review's binary convergence loop rubber-stamps and never converges
description: Correction of Error — a primed, severity-blind spec-review passed CLEAN over a real contradiction.
type: decision
---

# Correction of Error — spec-review's binary convergence loop rubber-stamps and never converges

**Date:** 2026-06-27 ·
**Severity:** medium ·
**Status:** root-caused

## What happened

Spec-reviewing the `release-column` spec, the convergence loop returned `SPEC_REVIEW:
CLEAN`. A subsequent **context-isolated ("blind")** re-review then found a real
self-contradiction — the spec puts release versions *on* the board, while a standing
board-conventions line (shipped in `worktree-per-card`) says "Release version … **not the
board**" — plus an AC `MAY`-vs-tasks conflict and a non-taxonomy status header. Four blind
passes found **2 → 3 → 1 → 5** findings: a mix of real contract violations and an unbounded
tail of subjective prose nits. The primed loop's `CLEAN` had surfaced none of them.

## Root cause

Two machinery gaps in spec-review's convergence loop (not a reviewer mistake):

1. **No severity — a binary verdict.** spec-review emits `CLEAN | FINDINGS`; *any* finding,
   a blocking contract violation or a taste-level comma, keeps the loop in `FINDINGS`. So it
   cannot converge over subjective prose (different judges flag different nits forever), and
   `CLEAN` carries no signal that nothing blocking remained. `code-review` already gates on
   `blocking`/`advisory`; spec-review was never brought to parity.
2. **A primable re-review.** The skill lets the author hand the reviewer a "here's what I
   changed" summary. A judge told what changed verifies rather than re-scrutinizes —
   **self-enhancement / confirmation bias**, a documented LLM-as-judge failure (self-preference;
   reward-hacking when the same context generates and judges). The `CLEAN` was a primed
   rubber-stamp; the blind pass, given only the artifact, caught what it missed.

## Blast radius

Every spec that passed spec-review `CLEAN` may carry an unflagged blocking defect or an
unconverged prose tail. Concretely, the **merged** `worktree-per-card` spec shipped with the
same non-taxonomy status-header defect the blind pass later caught. `code-review` is
unaffected by the *severity* gap (it already gates on `blocking`/`advisory`), but **shares the
blind-re-review gap**: its inter-round re-review is blind only by the runner, not by contract
(the SKILL even sanctions an inline pass), and its cross-model refuter is **DROP-only**
(precision) — so it cannot recover a blocking finding a primed re-review *missed*, the exact
failure mode here. The fix's US-2 therefore covers both review skills.

## The mechanical fix

`roadmap/specs/review-convergence/` brings spec-review to code-review's bar:

- spec-review findings carry **`blocking` | `advisory`** severity; the `FLAGGED:` footer
  lists **blocking only**; `SPEC_REVIEW: CLEAN` means **no unresolved blocking finding**
  (advisory may remain) — the loop converges on substance, not taste.
- the convergence re-pass is **blind**: the hook re-spawns fresh context and the skill
  **forbids priming** the reviewer with a change summary.
- **objective writing-style rules move to a deterministic linter**, so taste never enters the
  binary gate; the judge's prose findings are advisory.
- the loop terminates on **no new blocking** within the existing cap; the cap still escalates.

## Eval case spawned

Extend `evals/harness/spec-convergence-eval.sh` + the `spec-convergence` fixture with: (a) a
seeded **blocking** contradiction — the loop must hold the gate (`FINDINGS`); (b) a seeded
pure **prose nit** — the loop must reach `CLEAN` (advisory, non-blocking); (c) a
**primed-vs-blind** discrimination — a primed re-review misses a seeded contradiction the
blind pass catches. Each must fail the gate if the fix regresses.

## Promotion

The root cause is shared plugin machinery (`skills/spec-review`,
`scripts/spec-convergence-hook.sh`). The fix lands in the plugin and propagates on install;
the eval case lives in the plugin's eval harness.
