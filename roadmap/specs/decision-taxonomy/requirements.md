# Decision taxonomy — requirements

**Status:** Spec — requirements drafted (2026-06-29) — tracked on the [board](../../ROADMAP.md).

## Overview

Foundry's `type` taxonomy (`reference | architecture | guide | decision`) has two defects.

**The `decision` bucket is a misnamed catch-all.** It holds four genres of dated engineering
record — an ADR-style choice (Architecture Decision Record), a correction of error (COE), a
subsystem review/audit, and an investigation/experiment — yet is named after the one (ADR) it least
contains. Foundry's own knowledge base proves it: both `type: decision` files are COEs
(`knowledge/coe-template.md`, `knowledge/review-convergence-coe.md`); there are zero ADRs. (The
recommended three-genre layout folds investigation/experiment into `reviews/` as an analysis — design
Open question 2.)

**The taxonomy is missing the axis that governs maintenance: evergreen vs dated.**
`reference` / `architecture` / `guide` are **evergreen** — they describe current reality, so
drift from the code is a *defect*; they must be edited to current. A `decision`-class file is
**dated** — a point-in-time record that is *not wrong* when the code later changes, only
historical; it must be appended and superseded, never edited to current. The single `type`
field collapses the maintenance axis into genre, so the bucket fills with COEs and reviews while the
lifecycle discipline that should govern them is undocumented and unenforced.

This spec makes the evergreen/dated split explicit, disambiguates the dated genres, and
documents the immutable append/supersede lifecycle. It **weighs three designs** (see `design.md`)
— **C** genre-by-directory + metadata facets (the structure the maintainer shipped in the octant
repo, PR #15), **A** a `record` umbrella type + genre field, and **B** first-class genre types — and
**recommends C**. The acceptance criteria below are option-agnostic: they state the outcomes any
design must satisfy.

This is a breaking format change, taken pre-1.0 — the closed `type` set becomes `reference |
architecture | guide | dated` (`decision` retired to the `decisions/` folder); it lands as a
convention break with a migration, in lockstep across `plugins/foundry/templates/{verbatim,seeds}/`
and foundry's self-hosted copies.

## User stories

**US-1 Evergreen/dated axis is explicit.** As an agent or human curating the knowledge base, I
want the maintenance class of every concept stated, so I know whether to edit it to current or
to append-and-supersede.

- AC-1.1 THE SYSTEM SHALL classify each `type` as **evergreen** or **dated** in a machine-readable
  partition in `knowledge/knowledge-config.json`, so tooling and prose can treat the two classes
  differently.
- AC-1.2 WHEN the knowledge tool lists or indexes concepts, THE SYSTEM SHALL distinguish dated
  concepts from evergreen ones (a section, grouping, or marker), so a reader sees the class.
- AC-1.3 THE `knowledge-conventions` rule and the `knowledge` skill SHALL state the maintenance
  contract: an evergreen concept is edited to current and its drift from the code is a defect; a
  dated record is immutable once written.

**US-2 Dated genres are disambiguated.** As a producer of a dated record, I want it to have a genre
home, so a COE, a review, and a decision (ADR) are no longer one undifferentiated bucket.

- AC-2.1 THE SYSTEM SHALL give each dated record a genre home — correction of error (`coes/`),
  review/audit/survey (`reviews/`), or decision/ADR (`decisions/`) — replacing the `decision`
  catch-all. (Recommended mechanism: the directory; under Option A the genre is a frontmatter field.)
- AC-2.2 WHEN the knowledge tool runs `check`, IF a dated record is not under a genre directory,
  THEN it SHALL exit nonzero naming the file. (Under Option A the signal is a missing `genre` field.)
- AC-2.3 THE SYSTEM SHALL retire the misnomer: dated records SHALL route to per-genre homes, and
  `decision` SHALL be removed as a `type` value — reserved for the `decisions/` ADR folder. The dated
  maintenance class SHALL be typed `dated`, so a COE is `type: dated` in `coes/`, never typed
  `decision`. (The exact word `dated` is a `naming-standards` call — design Open question 1.)

**US-3 Immutable append/supersede lifecycle.** As a maintainer, I want dated records to accrete
rather than mutate, so history stays trustworthy and corrections are visible.

- AC-3.1 WHERE a dated record is corrected or overtaken, THE `knowledge-conventions` rule and the
  `knowledge` skill SHALL direct the editor to append a new record and mark the prior one
  `lifecycle: superseded` (or `historical`), never edit it to current.
- AC-3.2 THE SYSTEM SHALL surface non-current records as de-emphasized and last within their group
  in `list` / `index.md` / sidebar — delivered by [`okf-listing-fidelity`](../../ROADMAP.md); this
  spec depends on it and SHALL NOT duplicate it.
- AC-3.3 THE `knowledge` skill's coherence guidance SHALL name an edited-to-current dated record (a
  material content change with no new superseding record) as an incoherence to flag.

**US-4 Shipped as a convention break with a migration.** As a consumer of foundry, I want the
taxonomy change to migrate my repo automatically, so the rename does not silently break my
knowledge base.

- AC-4.1 THE SYSTEM SHALL ship the change as a convention break: a `references/migrations/`
  playbook, a registry-head row, and a `conventionVersion` bump, migrating existing dated records to
  their genre home (the COEs into `coes/`), retyping them `type: decision` → `type: dated`, and adding
  the `dated_types` partition.
- AC-4.2 THE migration detector SHALL key only on a structural signal the migration removes (a
  `type: decision` concept not yet under a genre directory, or a config with no `dated_types`
  partition), so an already-migrated repo never re-triggers (idempotent).
- AC-4.3 THE SYSTEM SHALL update every dependent artifact in lockstep on its own propagation axis:
  - **`templates/{verbatim,seeds}/` + self-host** — the closed `type` set (config + `knowledge.py`),
    the `knowledge-conventions` rule, the `coe-template`.
  - **Plugin source** (ships with the plugin install, no per-repo copy) — `okf.md` (Differences from
    OKF), the `knowledge` skill.
  - **Foundry's `knowledge/glossary.md`** — the **Type** entry and the new terms.

**US-5 The change is eval-gated.** As a maintainer, I want a discriminating eval, so the new lint
provably fails on the defect it forbids.

- AC-5.1 THE SYSTEM SHALL add eval cases that fail before the change and pass after: a dated record
  with no genre home fails `check`; the evergreen/dated partition is surfaced in generated output.

## Out of scope

- The lifecycle-surfacing mechanics in `list` / `index.md` / sidebar — shipped by
  `okf-listing-fidelity` (this spec consumes them).
- Any change to the evergreen types (`reference` / `architecture` / `guide`) themselves.
- Restructuring `log.md` (the change history) — separate from per-concept lifecycle.
