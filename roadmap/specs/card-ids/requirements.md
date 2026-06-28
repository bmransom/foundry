---
title: Card Ids — requirements
description: A stable, unique, gate-enforced identifier per board card.
---

> **Status:** In progress (2026-06-25) — tracked on the [board](../../ROADMAP.md).

# Requirements

## Problem

A card is a board row, but it has no stable identifier. The spec slug is epic-level
(many cards share `roadmap/specs/foundry-core/`), and `Depends on` references cards by
free-text nickname. Worktree/branch-per-card naming (`card/<id>`, `wt/<id>`) and
race-free claiming need a unique, slug-safe id — enforced by the gate, not by review.

## User story

As an agent working a foundry board with parallel peers, I want every claimable card to
carry a unique, slug-safe `Id`, so branch/worktree names are unambiguous and a duplicate
id cannot reach `main`.

## EARS acceptance criteria

- AC-1.1 WHEN the gate runs, THE SYSTEM SHALL fail if two cards share an `Id`.
- AC-1.2 WHEN the gate runs, THE SYSTEM SHALL fail if an `Id` is not slug-safe
  (`^[a-z0-9][a-z0-9-]*$`).
- AC-1.3 WHEN a card's `Status` is claimable (Ready / In progress / Validating), THE
  SYSTEM SHALL fail if its `Id` is empty.
- AC-1.4 WHEN a card table has no `Id` column, THE SYSTEM SHALL fail.
- AC-1.5 WHEN every `Id` is unique, slug-safe, and present where required, THE SYSTEM
  SHALL pass and report the card and id counts.
- AC-1.6 WHEN a card is Done, Backlog, Planned, Blocked, or Superseded, THE SYSTEM SHALL
  permit an empty `Id` (presence is scoped to claimable cards).

## Out of scope (follow-ups)

- Resolving `Depends on` nicknames to ids (a later lint tightening).
- Migrating existing **consumer** repos to the `Id` column (an `update` migration).
