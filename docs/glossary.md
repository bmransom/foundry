---
title: Foundry glossary — the ubiquitous language
description: The vocabulary contract for foundry's specs, code, and docs.
kind: reference
---

# Foundry glossary — the ubiquitous language

The vocabulary contract for foundry's specs, templates, skills, and docs. When code
and this file disagree, this file wins (and the code is debt to be migrated).
A new term names its prior art — the industry or stack standard it follows — or
records why none fits.

## Canonical terms

| Term | Definition | Replaces (now debt) |
|---|---|---|
| **Bootstrap** | The one-time act of installing the setup into a consumer repo: inspect → interview → copy → generate → verify. | scaffold (as a verb), init |
| **Consumer repo** | A repo that received the setup via bootstrap. Octant is consumer #1. | target repo, client repo |
| **Template** | A file foundry installs into a consumer repo. Three classes: *verbatim* (byte-identical everywhere, byte-checked), *seed* (copied once, then repo-owned), *generated* (produced per-repo by the bootstrap skill). | boilerplate, scaffold (as a noun) |
| **Seed** | A template copied once at bootstrap and then owned by the consumer repo (board, glossary, doc stubs, rules). Never byte-checked — divergence is the point. Database-seeding vocabulary. | starter, stub (as a class name) |
| **Version marker** | The `foundry-template: <name> v<N>` comment stamped into every verbatim template copy; what `/foundry:update` diffs against. | header, watermark |
| **Gate** | A verification command whose recorded PASS is the evaluator for done-ness. The quick gate runs pre-push and in CI; a heavy gate is optional and repo-specific. | check, validation step |
| **Fixture** | A small repo under `evals/fixtures/` that bootstrap evals run against. xUnit vocabulary. | sample repo, test repo |
| **Seeded defect** | A deliberate fault on a fixture branch (failing test, lint error, debt term) that a generated gate must catch. Grades gates by discrimination, not green-ness. Mutation-testing vocabulary. | mutation, fault injection |
| **COE** | Correction of Error: a dated record of a real failure the setup permitted. Closed only by a mechanical change (gate, lint, rule, or eval fixture). Promotes upstream to foundry when the root cause is shared machinery. AWS operational vocabulary. | postmortem (debt only when used for setup failures), retro |
| **Interview** | The bootstrap's question pass that supplies repo content: description, vocabulary seed, API surface, gate commands, isolation needs, unit of work for logging. | wizard, questionnaire |
| **Manifest** | `.foundry-manifest.json` in a consumer repo: the plugin version plus each installed verbatim file's template name, version, and content hash — how `/foundry:update` tells pristine from customized. Package-manager vocabulary (lockfile family). | lockfile (for this file), state file |
| **Wide event** | One structured record per unit of work carrying identity, release metadata, execution cost, and decision inputs — the canonical log line. The logging convention bootstrap installs. Stripe/Honeycomb vocabulary. | log spam (many fragmented lines per request) |
| **Card / Board** | One row of work on `docs/ROADMAP.md` / the board itself — the single source of truth for cross-spec status. | ticket, issue (for board rows) |
