---
title: Card Ids — tasks
description: Waves to ship the Id column and its gate lint.
---

> **Status:** In progress (2026-06-25) — tracked on the [board](../../ROADMAP.md).

# Tasks

## Wave 1 — the lint

- T1 `scripts/check-board.py`: parse card tables; enforce AC-1.1…1.6.
- T2 `scripts/test_check_board.py`: discrimination cases (dup, missing-on-claimable,
  malformed, no-Id-column) + a clean-board pass.
- T3 Verbatim twins under `plugins/foundry/templates/verbatim/scripts/`, byte-identical.
- Gate: `python3 scripts/test_check_board.py` passes; each seeded defect fails the lint.

## Wave 2 — migrate the board

- T4 Add the `Id` column to every `roadmap/ROADMAP.md` table; assign ids to claimable
  cards; add this feature's own card.
- T5 Update the `Board conventions` card-shape line to `Id | Work | Status | Spec | Depends on`.
- Gate: `python3 scripts/check-board.py` clean on the real board.

## Wave 3 — wire and propagate

- T6 `check-fast.sh`: add the `== board` stage.
- T7 Seed ROADMAP (`templates/seeds/roadmap/ROADMAP.md`) carries the `Id` column;
  `generate.md` adds the board check to the gate and the `Id` column to the card shape;
  `verify.md` lists the new verbatim scripts.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`.
