# Worktree-per-card — mechanics

The card's git lifecycle, referenced from the `code` skill's Plan, Build, and Finish
stages. Spec: `roadmap/specs/worktree-per-card/`.

## Claim and create the worktree (Plan)

A card is claimed by **creating its `card/<id>` branch** — its existence is the claim, so
no claim is committed to the default branch (which may be protected, where a direct claim
commit is neither always possible nor go-ahead-free):

```bash
git worktree add -b card/<id> wt/<id> origin/<default>
```

- `<id>` is the card's board `Id` (gate-enforced unique + slug-safe by `check-board.py`).
- Work in the worktree, never the shared primary checkout — a shared workspace overloads
  one branch across parallel sessions.
- The branch's existence (`git worktree list` locally; the remote branch once pushed) is
  the cross-agent claim signal. **First claim wins** — if the branch already exists or the
  card is owned, re-read the board and pick another.
- Don't mutate the board to claim; a card's board status rides the work's PR.

## Commit freely (Build)

A commit inside your worktree is a **private, recoverable checkpoint**, not a published
act. Commit each green step — stage explicit paths, never `git add -A` — and build the
spec's full scope confidently. No approval is needed to commit; the only outward act that
asks is the **push**.

## Done = merged (Finish)

A card is **Done when its `card/<id>` branch merges to the default branch with the required
gate green** — the merged PR's gate run is the recorded gate PASS, and branch protection
guarantees it ran before merge, so `Done` cannot land without it.

- **Ask before you push**, and never merge to the default branch without an explicit
  go-ahead (invariant with lifecycle-autonomy AC-2.4).
- Set the card's `Done` status **in the same PR that merges the work**, so it lands
  atomically with the merge — never a separate follow-up PR.
- `Validating` is **reserved** for a card that still needs a named post-merge check (e.g. a
  live verification) before `Done`, not a step every card passes through.
- Release/version is a separate axis — release-please / CHANGELOG, not the board.
- After the merge, retire the worktree: `scripts/worktree-retire.sh <path> --delete-branch`.
