# Migration: card-ids (convention 3 → 4)

Brings a repo to the convention-4 board layout: a unique, slug-safe **`Id`** column on every
card table, required on claimable cards (Ready / In progress / Validating) and enforced by
`check-board.py` in the gate. The update skill runs this on a clean tree, on a branch, and
verifies (`../../SKILL.md` §3 Migrate). Steps split into **primitives** (deterministic) and
**judgment** (read the repo, then decide).

## Detect

Applicable when the board predates the `Id` column:

- a `roadmap/ROADMAP.md` whose card-table header is `| Work | Status | … |` with **no `Id`
  column**, or
- a manifest `conventionVersion < 4`.

A correct migration adds the `Id` column, so the detector never re-triggers (idempotency).

## Preconditions

The update skill's preflight (`references/migrations/preflight.sh`) has already refused a dirty
tree and created `foundry/migrate-card-ids`. `check-board.py` ships at
`<plugin>/templates/verbatim/scripts/check-board.py`; the migration self-verifies with that
**bundled** copy (the repo's own copy + gate wiring arrive in §4/§6 + gate-sync, after Migrate).

## Plan (dry-run)

Report, before writing: each card table that gains the `Id` column, and the `Id` to assign each
**claimable** card. Write nothing until reported.

## Transform — primitives (deterministic)

For every card table on the board:

- Insert `Id` as the first column of the header row and `---` as the first column of the
  separator row.
- Prepend an empty `| ` cell to every existing card row (so the table stays well-formed).

## Transform — judgment

For each **claimable** card (Status in Ready / In progress / Validating), fill its `Id` with a
unique, slug-safe (`^[a-z0-9][a-z0-9-]*$`) handle derived from the card's Work — short, stable,
and unique across the whole board. A non-claimable card (Backlog / Planned / Done / Superseded)
may keep an empty `Id` unless it already has one. Preserve every other cell verbatim.

## Self-verify

- `python3 <plugin>/templates/verbatim/scripts/check-board.py roadmap/ROADMAP.md` passes (the
  bundled copy — the repo's own may not be installed yet).
- Every claimable card has a unique `Id`; the Detect signal no longer fires (the `Id` column is
  present).
