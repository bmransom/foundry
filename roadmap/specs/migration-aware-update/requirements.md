> **Status:** In progress (2026-06-14) — tracked on the [board](../../ROADMAP.md).

# Requirements — migration-aware update

## Overview

`/foundry:update` refreshes templates on a version bump but cannot cross a
*convention break* — a release that renames templates, moves directories, or
changes frontmatter (the OKF `docs/`→`knowledge/`+`roadmap/` break is the first).
On such a repo, plain update bolts the new tooling alongside the old: it installs
`knowledge.py` as "new", leaves `docs.py` orphaned, and never moves a file or
flips a field. This feature folds migration into update — the Angular `ng update`
model: update detects a convention break, runs the matching migration before the
standard refresh, and proves the result with the repo's own gate.

Migrations are version-gated playbooks in a registry, not codemods. The
agent orchestrates each one — detecting, sequencing, classifying seeds, and adapting
to repo drift — while the deterministic, must-not-vary steps (byte-exact recopy,
`knowledge.py index`, manifest regeneration) run through fixed primitives. The
consumer's gate, which shares no code with the migrator, is the acceptance test.
This keeps the mechanism agent-native and low-maintenance, and it accretes one entry
per future break.

A repo may be several breaks behind. Update sequences migrations by *convention
version* — a monotonic integer recorded in the manifest, bumped only by a break and
independent of the plugin's semver — applying each in order until the repo reaches
the plugin's convention version. A repo with none recorded (bootstrapped before
this feature) is placed by structural detection, then sequenced forward.

## User stories

### Story 1 — the consumer crosses every convention break in one command

- **As a** maintainer of a repo bootstrapped on an older foundry, perhaps several
  breaks behind
- **I want** `/foundry:update` to detect how far behind the repo is and migrate it
  across every break up to the current convention
- **So that** I do not hand-port directory layout, frontmatter, config, and the
  manifest, break by break

### Story 2 — migrations accrete without bloating update

- **As a** foundry maintainer
- **I want** each convention break expressed as a registered, version-gated
  playbook
- **So that** the update core stays lean and a new break is one new reference, one
  new eval fixture

### Story 3 — migration is safe and reversible

- **As a** user with a large or long-neglected repo
- **I want** the migration to require a clean baseline, preview every change, run on
  its own branch, and verify without blaming me for a gate that was already red
- **So that** I can review the diff, trust the result, and abandon it in one step if
  I do not like it

## Acceptance criteria

### Detection and safety

- **AC-1.1** WHEN `/foundry:update` runs AND the repo carries an old-convention
  marker — a manifest entry whose template no longer ships (`docs`, `test-docs`),
  `scripts/docs.py`, `docs/docs-config.json`, or a top-level `docs/` directory —
  THE SYSTEM SHALL select the applicable migration before the standard
  verbatim/seed comparison. A stray `kind:` field is migration *residue* (AC-3.2),
  not a trigger: the detector keys only on structural signals a correct migration
  removes, so an already-migrated repo never re-triggers.
- **AC-1.2** WHEN no old-convention marker is present, THE SYSTEM SHALL skip
  migration and run the standard update unchanged.
- **AC-1.3** IF the working tree is dirty, THE SYSTEM SHALL refuse to migrate and
  instruct the caller to commit a baseline first.
- **AC-1.4** WHEN one or more migrations are selected, THE SYSTEM SHALL present the
  planned chain — each migration's moves, transforms, and seed replacements, in
  order — as a dry-run report that writes nothing, before any file is changed.
- **AC-1.5** WHEN a migration will write AND the caller has not opted out, THE SYSTEM
  SHALL create and switch to a dedicated branch (`foundry/migrate-<id>`) before
  writing, leaving the working branch untouched until the caller reviews the diff and
  merges — blast-radius control for large repos.

### The OKF docs→knowledge migration (first registry entry)

- **AC-2.1** WHEN the OKF migration runs, THE SYSTEM SHALL move `docs/` concepts
  to `knowledge/`, `docs/ROADMAP.md` and `docs/BACKLOG.md` and a top-level
  `specs/` to `roadmap/`, the vitepress scaffold to `knowledge/`, and any
  crate-level `crates/*/docs/` to `crates/*/knowledge/`, preserving git history
  (rename, not delete-plus-create).
- **AC-2.2** WHEN the OKF migration runs, THE SYSTEM SHALL rename the `kind`
  frontmatter field to `type` on every concept and remove it from board files that
  are no longer concepts (`ROADMAP.md`, `BACKLOG.md`).
- **AC-2.3** WHEN the OKF migration runs, THE SYSTEM SHALL rewrite
  `docs/docs-config.json` to `knowledge/knowledge-config.json`, applying the OKF
  key renames (`kinds`→`types`, `doc_globs`→`concept_globs`,
  `exclude_paths`→`reserved_files`) and adding `index_title`, while carrying over
  every other key (`lifecycles`, `required_fields`, `exclude_substrings`,
  `exclude_prefixes`, `skill_ref_prefixes`) — the shipped `knowledge-config.json`
  seed is the authoritative shape. `reserved_files` SHALL list `index.md` and
  `log.md`, and `README.md` SHALL become a curated concept, not an exclusion.
- **AC-2.4** WHEN the OKF migration runs, THE SYSTEM SHALL replace the
  break-affected verbatim files byte-exact from the current templates —
  `scripts/{knowledge.py,test_knowledge.py,board.sh,worktree-retire.sh}` and
  `knowledge/{package.json,tsconfig.json,.vitepress/config.ts}`, renamed or moved
  from their `docs/` paths — and regenerate `.foundry-manifest.json` over the
  *complete* installed verbatim set (every file under `templates/verbatim/`,
  including the unaffected `pre-push` and `install-hooks.sh`), recording each
  file's template name, marker version, and sha256, plus the plugin and convention
  versions.
- **AC-2.5** WHEN the OKF migration runs, THE SYSTEM SHALL rewrite old-path
  references (`docs/`→`knowledge/` or `roadmap/`; bare `specs/`→`roadmap/specs/`)
  in every foundry-surface file that carries them — among them `AGENTS.md`,
  `scripts/check-fast.sh`, the rules, the CI workflow, and `.gitignore`, plus
  `scripts/vocab-lint.sh` and `scripts/agent-env.sh` where the repo has them. The
  target set is whatever the repo contains, not a fixed list.
- **AC-2.6** WHEN the OKF migration meets a pristine seed (marker and hash match
  the shipped seed), THE SYSTEM SHALL replace it with the current seed; WHEN it
  meets a customized seed, THE SYSTEM SHALL transform it in place and flag the
  divergence — reusing update's existing classification.
- **AC-2.7** WHEN the OKF migration completes, THE SYSTEM SHALL generate
  `knowledge/index.md` and append a dated entry to `knowledge/log.md`.

### Verification

- **AC-3.1** WHEN a migration finishes, THE SYSTEM SHALL require the
  migration-specific checks green (`knowledge.py check`, structure, completeness,
  manifest sha-match) AND require the repo's canonical gate not to regress against a
  pre-migration baseline — a gate already red before the migration is reported, never
  blamed on it or forced through. THE SYSTEM SHALL ask before committing or merging.
- **AC-3.2** WHERE old-convention residue remains after a migration — a `kind:`
  field, a `docs/` path reference, `docs.py`, a manifest sha that does not match
  disk — THE SYSTEM SHALL report it as a completeness failure rather than a PASS.

### Sequencing across multiple convention breaks

- **AC-4.1** THE registry SHALL be an ordered list keyed by *convention version*;
  WHEN update runs, THE SYSTEM SHALL apply, in ascending order, every migration
  whose convention version exceeds the repo's current convention version and is at
  most the plugin's.
- **AC-4.2** WHEN the manifest records a `conventionVersion`, THE SYSTEM SHALL take
  it as the starting point; WHEN it does not (a repo bootstrapped before this
  feature), THE SYSTEM SHALL infer the starting point by structural detection
  (AC-1.1) and treat the repo as the earliest convention whose markers it carries.
- **AC-4.3** WHEN more than one migration applies, THE SYSTEM SHALL run them
  sequentially so each operates on the previous migration's output, re-running the
  structure and frontmatter checks between steps.
- **AC-4.4** Each migration SHALL be idempotent: WHEN run against a repo already at
  or beyond its target convention, its detector SHALL NOT fire and it SHALL make no
  change — so an up-to-date or partially hand-migrated repo converges without error.
- **AC-4.5** IF a migration in the chain fails its post-step check, THE SYSTEM SHALL
  stop at that migration, preserve the migrations already applied, and report which
  one failed — never continue past a broken step.
- **AC-4.6** WHEN the chain completes, THE SYSTEM SHALL record the plugin's
  convention version in the manifest, so the next update is version-gated and skips
  detection.

## Out of scope

- Migrating without the caller running `/foundry:update` — no background or CI
  migration.
- Migrating a dirty or uncommitted repo (AC-1.3 refuses).
- Convention breaks other than OKF — the registry supports them; only the OKF
  entry ships now.
- Rewriting application source or business logic — the migration touches only the
  foundry setup surface (tooling, config, knowledge, roadmap, AGENTS.md, CI,
  hooks).
- A general-purpose codemod engine — migrations are agent-executed playbooks
  verified by the gate, not parsers.
- Rolling a migration back — recovery is `git revert` of the migration commit, not
  an inverse migration.

## Dependencies

- The OKF convention (`roadmap/specs/okf-alignment/`) — the migration's target
  shape and the source of the new templates and seeds.
- update's pristine/customized/new classification — reused for seed handling
  (AC-2.6).
- The manifest mechanism (bootstrap SKILL.md §3 Copy) — regenerated by the
  migration, now also carrying `conventionVersion` (AC-2.4, AC-4.6).

## Verification plan (detailed in design)

An eval fixture repo on the old `docs/` convention; the migration runs; the eval —
not the migrator — asserts the new-convention structure, `knowledge.py check`
green, manifest sha-match, and zero residue. Discrimination: a deliberately
incomplete migration must fail a harness-owned residue scan; the migrator's own
checks never grade it (independent verification). The eval also proves the chain
sequences across two hops, not one. Design carries the mechanism.
