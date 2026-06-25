> **Status:** Draft (2026-06-25) — design pending approval.
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — lifecycle autonomy

## Summary

An autonomy dial for the `code` lifecycle. At Frame, the user sets — once — how far the
lifecycle runs before handing back: an **autonomy level** (Supervised / Guided /
Autonomous) and a **stop-point** (this feature, a named board card, the epic, or the
whole roadmap). The level governs gate behavior and handback cadence; the stop-point
bounds the run. The dial is harness-aware: a Claude Code `/loop` prompt or a Codex
`/goal` supplies the directive instead of an interactive prompt, and it is never
re-asked mid-run.

## Glossary impact

- **Autonomy level** — how much of the lifecycle the agent runs unattended before
  handing back: Supervised, Guided, or Autonomous. Prior art: Codex approval modes
  (Read-only / Auto / Full Access) and the role-based agent-autonomy levels
  (operator → observer); foundry binds the level to its lifecycle gates.
- **Stop-point** — the boundary that ends an autonomous run: a feature, a named board
  card, the current epic, or the roadmap.

## US-1 — Set autonomy once, at the start

- AC-1.1 WHEN the `code` lifecycle begins at Frame AND no autonomy directive is already
  supplied, THE SYSTEM SHALL ask the user — through the harness's question tool — for an
  autonomy level and a stop-point.
- AC-1.2 WHEN the user answers, THE SYSTEM SHALL record the level and stop-point in
  run-state at `.foundry/tmp/lifecycle-run.json` so the directive survives a context
  reset or a loop iteration.
- AC-1.3 WHEN a directive already exists — a run-state record, a `/loop` prompt that
  names it, or a Codex `/goal` — THE SYSTEM SHALL read that directive and SHALL NOT
  re-ask.
- AC-1.4 WHEN the harness has no question tool and no directive is supplied, THE SYSTEM
  SHALL default to Supervised / this-feature and say so before proceeding.

## US-2 — The level governs who resolves a judgment call

A **hard blocker** is a condition the agent cannot proceed past: a gate that will not
pass after its retry budget, a missing dependency, or an ambiguity with no defensible
resolution. A **soft fork** is a judgment call with more than one defensible answer: an
ambiguous AC the agent can reasonably interpret, a design choice with real tradeoffs, or
a blocking review finding with several reasonable fixes. A hard blocker halts every level
(AC-3.4); the level decides who resolves a soft fork.

- AC-2.1 WHEN the level is Supervised, THE SYSTEM SHALL drive exactly one feature to
  Finish, then stop and hand back; the Design-approval and commit gates SHALL ask the
  user as the base lifecycle does — it asks at every gate.
- AC-2.2 WHEN the level is Guided, THE SYSTEM SHALL self-approve an unambiguous Design and
  commit on a feature branch, BUT SHALL stop and ask the user at every soft fork,
  auto-proceeding only when the path is unambiguous — it asks at decisions.
- AC-2.3 WHEN the level is Autonomous, THE SYSTEM SHALL resolve a soft fork itself —
  choosing the most defensible option and recording the rationale in the stop-point
  summary — and SHALL surface only at the stop-point or a hard blocker — it asks at
  nothing but hard blockers (human-on-the-loop).
- AC-2.4 Regardless of level, THE SYSTEM SHALL NOT push or merge to the default branch
  without an explicit user go-ahead — the "ask before push" boundary is invariant.

## US-3 — The stop-point bounds the run

- AC-3.1 THE stop-point SHALL be one of: this feature, a named board card, the current
  epic, or the whole roadmap.
- AC-3.2 WHEN a feature reaches Finish AND the stop-point is not reached AND the level
  is Guided or Autonomous, THE SYSTEM SHALL claim the next eligible roadmap card and
  re-enter Frame for it.
- AC-3.3 WHEN the stop-point is reached, the roadmap is exhausted, or a hard blocker
  occurs, THE SYSTEM SHALL stop and report a run summary: features finished, the gate
  PASS for each, decisions taken without asking, and where it stopped and why.
- AC-3.4 A hard blocker — a gate that cannot pass, a missing dependency, or an ambiguity
  with no defensible resolution — SHALL halt the run and hand back with the specific
  blocker, at every level. (A soft fork that the agent can resolve is not a hard blocker;
  AC-2.2/AC-2.3 govern it.)

## US-4 — Harness integration

- AC-4.1 Under Claude Code `/loop`, THE SYSTEM SHALL treat the loop as the driver: the
  stop-point decides when to stop re-arming the loop, and the directive is read from the
  loop prompt or run-state, never re-asked per iteration.
- AC-4.2 Under Codex `/goal`, THE SYSTEM SHALL treat the goal as the scope directive and
  the Codex approval mode as the gate behavior, and SHALL NOT re-ask either.
- AC-4.3 THE run summary (AC-3.3) SHALL name "stop-point reached" in a form the driving
  command can act on — for `/loop`, the signal to stop re-arming.

## Metrics

- Honored stop-point: a run stops at exactly its stop-point (or a hard blocker), never
  past it — measured by the eval.
- No runaway: zero pushes or merges to the default branch without a go-ahead (AC-2.4).
- No re-ask: a directive supplied by `/loop` or `/goal` is read, not re-prompted.
