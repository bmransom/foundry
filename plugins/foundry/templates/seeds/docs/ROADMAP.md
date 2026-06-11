---
title: Roadmap
description: The tracked kanban board — the single source of truth for cross-spec status.
kind: reference
---

<!-- foundry-seed: roadmap v1 -->

# Roadmap

This board is the single source of truth for cross-spec status, sequencing, and
ownership. When a per-feature spec and this board disagree, the board wins; every
spec carries a status header that points here.

## Board conventions

Render the board with `scripts/board.sh` (filter to one epic: `scripts/board.sh "Epic 0"`).

- A **card** is one table row: `Work | Status | Spec | Depends on`. Claim a card by
  adding `(@<owner>)` to its Work cell; never take a card another agent owns.
  Respect the Depends-on column.
- A card's **status** is its column: `Backlog → Ready → In progress → Validating →
  Done` (+ `Superseded`, terminal). `Blocked` and the owner are flags, not columns.
- The dashboard groups cards by **epic**; the epic order is the priority order.
- **`Done` requires a recorded gate PASS** — the gate is the evaluator, not the
  author's assertion.
- The un-carded idea pool is `docs/BACKLOG.md`; an idea stays there until committed.

### Status taxonomy

Use these words in board tables and spec status headers.

| Status | Meaning |
|---|---|
| Done | Implemented and verified by a recorded gate PASS; no active follow-up beyond normal maintenance. |
| Validating | Code landed; the repo's canonical gate is running. |
| In progress | Partially implemented, being hardened, or recently landed with known follow-up. |
| Ready | Spec'd — `specs/<feature>/` design and tasks approved, prerequisites met; claimable. |
| Planned | Accepted direction; not started, or scheduled behind prerequisites. |
| Backlog | Captured, not yet committed to build. |
| Blocked | Direction known; work waits on an external dependency or an earlier workstream. |
| Superseded | Preserved for history or rationale; no longer the forward plan. |

Use `Done`, never "complete", for implementation state.

## Standing rules

**Naming.** `docs/glossary.md` is the vocabulary contract. Inline the most-violated
glossary rules here as they emerge.

## Status Dashboard

### Epic 0 — `<the first epic>`

| Work | Status | Spec | Depends on |
|---|---|---|---|
