---
title: Foundry Roadmap
description: The tracked kanban board — the single source of truth for cross-spec status.
kind: reference
---

# Foundry Roadmap

This board is the single source of truth for cross-spec status, sequencing, and
ownership. When a per-feature spec and this board disagree, the board wins; every spec
carries a status header that points here.

## Board conventions

- A **card** is one table row: `Work | Status | Spec | Depends on`. Claim a card by
  adding `(@<owner>)` to its Work cell.
- Status flow: `Backlog → Ready → In progress → Validating → Done` (+ `Planned`,
  `Blocked` as a flag, `Superseded` terminal).
- **`Done` requires a recorded gate PASS** once the gate exists — the gate is the
  evaluator, not the author's assertion.

## Standing rules

**Naming.** `knowledge/glossary.md` is the vocabulary contract. In particular: a *template*
is a file foundry copies or renders into a consumer repo; a *fixture* is an eval
target repo; a *seeded defect* is a deliberate fault a generated gate must catch.

**Mechanisms, not content.** No template carries any repo's entity
model, forbidden terms, standing rules, or gate commands.

## Status Dashboard

### Epic 0 — Foundry v1

| Work | Status | Spec | Depends on |
|---|---|---|---|
| foundry-core spec: requirements + design | Done — spec approved 2026-06-10 | `roadmap/specs/foundry-core/` | — |
| Plugin skeleton: marketplace.json, plugin.json, repo self-host scaffold, `check-fast.sh` + self-host byte-identity gate | Done — gate recorded 2026-06-10: check-fast: PASS | `roadmap/specs/foundry-core/` | spec approval |
| Template extraction from the reference repo (@main): docs.py (parameterized), board.sh, vitepress scaffold, ROADMAP/glossary/spec-conventions/COE templates, githooks, worktree-retire | Done — gate recorded 2026-06-10: check-fast: PASS | `roadmap/specs/foundry-core/` | plugin skeleton |
| `code` lifecycle skill, generalized (reads repo AGENTS.md for commands/paths) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | template extraction |
| `spec-reviewer` agent, generalized (entity model read from repo glossary) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | template extraction |
| `bootstrap` skill: inspect → interview → copy → generate → verify (@main) | Done — gate recorded 2026-06-11: check-fast: PASS; smoke bootstrap of /tmp/wclip green end-to-end | `roadmap/specs/foundry-core/` | template extraction |
| `update` skill: version-marker diff + refresh (@main) | Done — gate recorded 2026-06-11: check-fast: PASS; smoke update of /tmp/wclip green (legacy backfill, refresh, customization protection, seed announce) | `roadmap/specs/foundry-core/` | bootstrap skill |
| Evals L1–L2: fixtures (Rust CLI, Python service, TS monorepo), harness, seeded defects, gate-discrimination checks (@main) | Done — 2026-06-11: full headless sweep green — python-service 51/51, rust-cli 47/47, ts-monorepo 46/46, update-eval 11/11; check-fast: PASS | `roadmap/specs/foundry-core/` | bootstrap skill |
| Evals L3: spec-reviewer precision/recall suite; lifecycle artifact checks (@main) | Done — 2026-06-12: reviewer-eval mean recall 0.967, 0 decoys; lifecycle-eval 7/7; plugin bumped to v1.0.0 (AC-2.3) | `roadmap/specs/foundry-core/` | Evals L1–L2 |
| COE mechanism: template (landed Wave 2), promote-upstream flow, eval-accretion rule (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | plugin skeleton |
| Reference-repo retrofit: consume foundry, move generic skill content upstream, keep domain-specific skills local | Backlog | spec to write | bootstrap skill |

### Epic 1 — Navigation eval + correctness/cost insight

| Work | Status | Spec | Depends on |
|---|---|---|---|
| navigation-eval spec: requirements + design + tasks | Done — approved 2026-06-13 (spec-reviewer applied) | `roadmap/specs/navigation-eval/` | — |
| Nav-eval harness: fixture (gold span + decoys, 3 doc sizes), arms (full-load / native / docs.py), grader, token capture | Validating — built, gate green, live pilot N=1 ran | `roadmap/specs/navigation-eval/` | spec approval |
| Correctness-vs-context-cost visualization (SVG plotter, reusable) | Validating — built + unit-tested; nav chart generated. Cross-eval token wiring (reviewer/bootstrap/lifecycle) still TODO | `roadmap/specs/navigation-eval/` | token capture |
| Pilot finding (N=1): all arms answer correctly (fixture non-discriminating on correctness); content loaded native ~201 < disclosure ~1.2k < full-load ~13k → disclosure protocol not necessary. Caveats: N=1, recall metric + arm enforcement need work | Validating | `roadmap/specs/navigation-eval/` | harness |
| Breadth sweep + hybrid arm: corpus-size fixture, 5 arms (incl. hybrid grep+docs.py), cost-vs-size crossover chart | Validating — live sweep N=1 (5/25/100) done. Finding: all arms correct at every size; native grep leanest (~219 @100) while the docs.py catalog (`list`) is O(N), the most expensive (~1439 @100) → disclosure does NOT pay off for greppable lookups. Untested regime: non-greppable / browse-by-topic queries | `roadmap/specs/navigation-eval/` | nav-eval harness |
