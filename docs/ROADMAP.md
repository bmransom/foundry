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

**Naming.** `docs/glossary.md` is the vocabulary contract. In particular: a *template*
is a file foundry copies or renders into a consumer repo; a *fixture* is an eval
target repo; a *seeded defect* is a deliberate fault a generated gate must catch.

**Mechanisms, not content.** No template carries octant's (or any repo's) entity
model, forbidden terms, standing rules, or gate commands.

## Status Dashboard

### Epic 0 — Foundry v1

| Work | Status | Spec | Depends on |
|---|---|---|---|
| foundry-core spec: requirements + design | Done — spec approved 2026-06-10 | `specs/foundry-core/` | — |
| Plugin skeleton: marketplace.json, plugin.json, repo self-host scaffold, `check-fast.sh` + self-host byte-identity gate | Done — gate recorded 2026-06-10: check-fast: PASS | `specs/foundry-core/` | spec approval |
| Template extraction from octant (@main): docs.py (parameterized), board.sh, vitepress scaffold, ROADMAP/glossary/spec-conventions/COE templates, githooks, worktree-retire | Done — gate recorded 2026-06-10: check-fast: PASS | `specs/foundry-core/` | plugin skeleton |
| `code` lifecycle skill, generalized (reads repo AGENTS.md for commands/paths) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `specs/foundry-core/` | template extraction |
| `spec-reviewer` agent, generalized (entity model read from repo glossary) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `specs/foundry-core/` | template extraction |
| `bootstrap` skill: inspect → interview → copy → generate → verify | Ready | `specs/foundry-core/` | template extraction |
| `update` skill: version-marker diff + refresh | Planned | `specs/foundry-core/` | bootstrap skill |
| Evals L1–L2: fixtures (Rust CLI, Python service, TS monorepo), harness, seeded defects, gate-discrimination checks | Planned | `specs/foundry-core/` | bootstrap skill |
| Evals L3: spec-reviewer precision/recall suite; lifecycle artifact checks | Planned | `specs/foundry-core/` | Evals L1–L2 |
| COE mechanism: template (landed Wave 2), promote-upstream flow, eval-accretion rule (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `specs/foundry-core/` | plugin skeleton |
| Octant retrofit: consume foundry, move generic skill content upstream, keep lp-result-triage local | Backlog | spec to write | bootstrap skill |
