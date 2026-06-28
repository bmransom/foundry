> **Status:** Draft (2026-06-27) — design pending approval.
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — worktree-per-card

## Summary

Establish the card's git lifecycle in the `code` skill: each board card runs in its own
git worktree on its own branch, the agent commits each green step as a recoverable
checkpoint, and the work integrates by merging that branch to the default branch — at which
point the card is **Done**. This replaces the prior model (ask before every commit; branch
on the default branch; `Done` meaning "shipped in a release"). It is the working model that
[`lifecycle-autonomy`](../lifecycle-autonomy/requirements.md) drives: the dial decides how
far the lifecycle runs and who resolves a fork; this decides how the work is isolated,
checkpointed, and integrated. The merge-to-default boundary is shared and invariant
(lifecycle-autonomy AC-2.4).

## Glossary impact

- **Done** (board status) — redefined to mean **merged to the default branch with the
  required gate green**, not "shipped in a release." Prior art: trunk-based development,
  where work is "done" when it integrates to trunk; release/version tracking is a separate
  axis (deferred `Release` column; release-please/CHANGELOG carries it today). No new
  canonical name — this refines an existing board status, recorded in `knowledge/log.md`.
- Reuses the glossary **Card id** entry's names: the branch is `card/<id>`, the worktree
  directory is `wt/<id>`.

## US-1 — One worktree per card

- AC-1.1 WHEN work on a card begins (Plan stage), THE SYSTEM SHALL create a dedicated git
  worktree on a dedicated branch off the latest default branch, named from the card's `Id`:
  `git worktree add -b card/<id> wt/<id> origin/<default>`.
- AC-1.2 THE SYSTEM SHALL NOT do card work in the shared primary checkout.
- AC-1.3 WHEN a card's work lands or is abandoned, THE SYSTEM SHALL retire the worktree
  with `scripts/worktree-retire.sh` (note-protection first) and delete the merged branch.

## US-2 — Commit freely; the push is the only ask

- AC-2.1 WHILE building in a worktree, THE SYSTEM SHALL commit each green step as a
  recoverable checkpoint, staging **explicit paths** (never `git add -A`, since the tree
  may be shared by parallel agents).
- AC-2.2 THE SYSTEM SHALL NOT require user approval to commit within a worktree — a local
  commit is a private, recoverable checkpoint, so the agent builds the spec's full scope
  confidently.
- AC-2.3 THE SYSTEM SHALL ask the user before pushing a branch to a remote.
- AC-2.4 THE SYSTEM SHALL NOT merge to the default branch without an explicit user
  go-ahead (invariant with lifecycle-autonomy AC-2.4).

## US-3 — Done = merged; condense Validating

- AC-3.1 WHEN a card's branch merges to the default branch with the required gate green,
  THE SYSTEM SHALL treat the card as **Done**; the merged PR's gate run is the recorded
  gate PASS that `Done` requires.
- AC-3.2 THE SYSTEM SHALL set the card's `Done` status **in the same PR that merges the
  work**, so the status lands atomically with the merge and no separate follow-up PR is
  needed.
- AC-3.3 THE status flow SHALL be `Backlog → Ready → In progress → Done`, with
  `Validating` **reserved** for a card that still needs a named post-merge verification
  (e.g. a live check) before `Done` — not a mandatory step every card passes through.
- AC-3.4 THE board conventions, the seed ROADMAP, and `AGENTS.md` SHALL state `Done =
  merged` consistently, removing the prior Epic-0 ("gate recorded") vs Epic-6 ("shipped in
  vX") inconsistency. Release/version tracking is out of scope here (deferred `Release`
  column).

## US-4 — Claiming a card

- AC-4.1 THE SYSTEM SHALL claim a card by creating its `card/<id>` branch and `wt/<id>`
  worktree; it SHALL NOT commit a claim to the default branch (which may be protected, so a
  direct claim commit is neither always possible nor go-ahead-free).
- AC-4.2 THE existence of the `card/<id>` branch — locally through `git worktree list`
  (worktrees share one `.git`) and, once pushed, on the remote — SHALL be the cross-agent
  claim signal.
- AC-4.3 WHEN a card's board status changes (e.g. to `In progress` or `Done`), THE SYSTEM
  SHALL make that change in the work's PR, not in a separate default-branch commit.
- AC-4.4 WHEN a `card/<id>` branch already exists or the card is owned, THE SYSTEM SHALL
  re-read the board and pick another card — first claim wins.

## Metrics

- No work on the primary checkout: a card's commits land on its `card/<id>` branch, never
  directly on the shared default branch — asserted by the lifecycle eval.
- No runaway: zero merges to the default branch without a go-ahead (AC-2.4).
- Status consistency: `check-board.py` plus a static doc check confirm the conventions,
  seed, and `AGENTS.md` state `Done = merged` with no "shipped in vX" gate wording.
