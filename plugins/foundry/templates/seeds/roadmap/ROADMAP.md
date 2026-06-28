---
title: Roadmap
description: The tracked kanban board — the single source of truth for cross-spec status.
---

<!-- foundry-seed: roadmap v2 -->

# Roadmap

## Board conventions

Run `scripts/board.sh` to render the board; `scripts/board.sh "Epic 0"` filters to one epic.

- A **card** is one table row: `Id | Work | Status | Spec | Depends on`. The `Id` is a
  unique, slug-safe (`^[a-z0-9][a-z0-9-]*$`) handle — required on claimable cards (Ready /
  In progress / Validating), enforced by `scripts/check-board.py` in the gate.
- **Claim a card by creating its `card/<id>` branch** and `wt/<id>` worktree off the
  default branch (`git worktree add -b card/<id> wt/<id> origin/<default>`); the branch's
  existence is the claim — first claim wins, never take an owned card. Don't commit a claim
  to the default branch; a card's board status rides the work's PR. Respect the Depends-on column.
- A card's **status** is its column: `Backlog → Ready → In progress → Done`
  (+ `Superseded`, terminal). `Validating` is reserved for a card needing a named
  post-merge check before `Done`. `Blocked` and the owner are flags, not columns.
- The dashboard groups cards by **epic**; the epic order is the priority order.
- **`Done` = merged to the default branch with the gate green** — the merged PR's gate run
  is the recorded PASS; set `Done` in the merging PR. Release version lives in the
  changelog, not the board.
- The un-carded idea pool is `roadmap/BACKLOG.md`; an idea stays there until committed.

### Status taxonomy

Use these words in board tables and spec status headers.

| Status | Meaning |
|---|---|
| Done | Merged to the default branch with the gate green (the merged PR's recorded PASS). |
| Validating | Reserved: merged, but a named post-merge check (e.g. a live verification) runs before `Done`. |
| In progress | Claimed — a `card/<id>` branch/PR is open; being built or hardened. |
| Ready | Spec'd — `roadmap/specs/<feature>/` design and tasks approved, prerequisites met; claimable. |
| Planned | Accepted direction; not started, or scheduled behind prerequisites. |
| Backlog | Captured, not yet committed to build. |
| Blocked | Direction known; work waits on an external dependency or an earlier workstream. |
| Superseded | Preserved for history or rationale; no longer the forward plan. |

## Standing rules

**Naming.** `knowledge/glossary.md` is the vocabulary contract. Use `Done`, never "complete", for implementation state. Inline the most-violated glossary rules here as they emerge.
- The board wins over any per-feature spec.
- Every spec status header points here.

## Status Dashboard

### Epic 0 — `<the first epic>`

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
