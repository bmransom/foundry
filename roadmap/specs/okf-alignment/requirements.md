# OKF alignment — requirements

**Status:** Spec — requirements drafted (2026-06-14) — tracked on the [board](../../ROADMAP.md).

## Overview

Align foundry's knowledge subsystem to the [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (OKF v0.1) so the knowledge base is interoperable and internally consistent. Four moves: rename the classification field `kind`→`type`; adopt one vocabulary — **knowledge** (base, tool) and **concept** (unit) — retiring "docs"; make `index.md` an OKF directory listing that doubles as the site home; add a reserved `log.md` change log. This is a breaking format change, taken pre-1.0 while there are zero consumers. Each change lands in two trees in lockstep — `plugins/foundry/templates/{verbatim,seeds}/` (distributed) and foundry's own self-hosted copies. It also completes the separation the directory refactor began: the OKF/concept format applies to the **knowledge base alone**; the roadmap (board + specs) and features are a separate subsystem and carry no concept frontmatter.

## User stories

**US-1 OKF-conformant format.** As a foundry maintainer, I want every concept file to follow OKF's required shape, so the knowledge base reads correctly to OKF-aware agents and tools.

- AC-1.1 WHERE a non-reserved markdown file exists under `knowledge/`, THE SYSTEM SHALL require a non-empty `type` frontmatter field, replacing `kind`.
- AC-1.2 WHEN the knowledge tool runs `check`, IF a non-reserved `knowledge/**/*.md` file lacks a parseable, non-empty `type`, THEN it SHALL exit nonzero naming the file.
- AC-1.3 THE SYSTEM SHALL treat `knowledge/index.md` and `knowledge/log.md` as reserved files (no frontmatter) and exclude them from the `type` lint.
- AC-1.4 WHERE `knowledge/index.md` exists, THE SYSTEM SHALL render it as both an OKF directory listing (no frontmatter; section headings over `* [Title](/url) - description` entries) and the vitepress site home, with no `layout: home` hero.
- AC-1.5 THE SYSTEM SHALL keep `type` values constrained to the enumerated set `reference | architecture | guide | decision` — foundry remains stricter than OKF's open-string `type` by deliberate choice (curated knowledge base).
- AC-1.6 THE SYSTEM SHALL scope the concept format to `knowledge/`. Roadmap and features files (`roadmap/ROADMAP.md`, `roadmap/BACKLOG.md`, `roadmap/specs/**`, `features/**`) are not concepts and SHALL NOT carry `type`/`kind` frontmatter; the vestigial `kind: reference` on these files — foundry's own and the seeds — SHALL be removed, preserving any `foundry-seed:` marker.

**US-2 One vocabulary.** As an agent or human working in the repo, I want a single term per thing across the tool, prose, skills, agents, and rules, so the `docs`/`knowledge` duality is gone.

- AC-2.1 THE SYSTEM SHALL name the navigation tool `scripts/knowledge.py` (renamed from `docs.py`), preserving its subcommands, and SHALL set the manifest template identifier and version marker to `knowledge` (renamed from `docs`).
- AC-2.2 WHERE foundry prose, skills, agents, or rules name the subsystem, THE SYSTEM SHALL use "knowledge" for the base/tool and "concept" for the unit; "doc"/"docs" SHALL NOT name the tool, unit, or collection (the ordinary-English word "documentation" is permitted).
- AC-2.3 THE SYSTEM SHALL rename the steering rule `docs-conventions.md`→`knowledge-conventions.md` and combine its naming and prose guidance under one `## Names and prose` heading, matching `spec-conventions.md` (also combined).

**US-3 Knowledge change log.** As a maintainer, I want a history of knowledge-base edits separate from code history, so concept changes are recorded where COEs (error corrections) and `CHANGELOG.md` (code releases) do not reach.

- AC-3.1 THE SYSTEM SHALL provide a reserved `knowledge/log.md` and a seed copy, in OKF §7 form: no frontmatter; ISO-8601 `YYYY-MM-DD` date headings, newest first; entries prefixed `**Update**`, `**Creation**`, or similar.
- AC-3.2 WHERE a concept is added or materially changed, the `knowledge-conventions` rule SHALL direct the editor to record it in `knowledge/log.md`.

**US-4 Bootstrap and self-host stay in lockstep.** As a maintainer, I want the distributed templates, the eval harness, and foundry's own instance to migrate together, so a fresh bootstrap yields the OKF-aligned base and no gate regresses.

- AC-4.1 WHEN a repo is bootstrapped, THE SYSTEM SHALL install the OKF-aligned knowledge base (`knowledge.py` verbatim, `type`-based seed concepts, reserved `index.md`/`log.md`), verified by the bootstrap eval's expectations.
- AC-4.2 THE SYSTEM SHALL keep foundry's self-hosted copies byte-identical to `templates/verbatim/` (the `knowledge.py` rename touches both trees), enforced by the byte-identity gate.
- AC-4.3 WHEN the reviewer eval runs, THE SYSTEM SHALL use `type` for finding-category labels in `answer-key.json` and `test_score_review.py`; scorer logic SHALL NOT change (it does not read the field).
- AC-4.4 WHEN `scripts/check-fast.sh` runs after the migration, THE SYSTEM SHALL exit 0 (every gate green: byte-identity, knowledge check, context-budget, script tests).

## Out of scope

- Opening `type` to arbitrary strings, or changing the four type values themselves.
- Renaming the reviewer eval's scorer logic or finding semantics (only the `kind`→`type` label).
- Exhaustive OKF conformance beyond `type` + reserved `index.md`/`log.md` (e.g., formal Concept IDs, bundle-relative absolute-link rewriting) — foundry is OKF-*compatible*, not certified conformant.
- Migrating existing consumer repos (there are none) or providing a `kind`→`type` back-compat shim.
- Retaining the vitepress hero landing (removed as a consequence of AC-1.4, not a goal).
- Applying the OKF/concept format to the roadmap or features subsystems — they are deliberately *not* knowledge bundles (AC-1.6 strips their leftover frontmatter rather than migrating it).

## Dependencies

- The `docs/`→`knowledge/` + `roadmap/` directory refactor (landed, commit `467abf7`).
- Gates: byte-identity, the knowledge (ex-docs) check + `test_docs.py`, context-budget.
- Harnesses: `bootstrap-eval.sh` + fixture `expectations.json`; `reviewer-eval.sh` + `score_review.py`; the navigation-eval fixtures (which generate `type` frontmatter and invoke the knowledge tool).
- External reference: OKF v0.1 SPEC (§6 `index.md`, §7 `log.md`, §9 conformance).
