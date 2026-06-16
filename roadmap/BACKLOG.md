---
title: Backlog
description: The idea pool — captured, not yet committed to the board.
---

<!-- foundry-seed: backlog v1 -->

# Backlog

The idea pool. An idea stays here, off the board, until it is committed to build —
then it becomes a card on `roadmap/ROADMAP.md`.

| Idea | Why | Source |
|---|---|---|
| lifecycle-eval `--grade-only` should take the feature keyword as an arg | It hardcodes "version", so re-grading a non-version feature run checks the wrong board row | Wave 7 final review |
| reviewer-eval signature matching: many-tokens-per-violation or match-by-line | A correct flag that quotes a different substring of the violation than the answer-key token scores a false miss (V9, run 2) | Wave 7 Task 7.2 |
| Plugin-side seed changelog (per-seed version history) | A seed announcement can only diff repo-copy vs current plugin seed, burying the upstream change in repo-owned divergence | Wave 5 update smoke, design question 5 |
| migration-eval `migration-rust` fixture (Rust workspace; `crates/*/docs/`→`crates/*/knowledge/`) | The only untested transform path — crate-level concepts (AC-2.1); book-copilot had no crates | migration-aware-update tier-2 |
| migration-eval `migration-python` fixture (service; ruff/pytest gate) | Confirm gate rewrite + no-regression on a non-TS stack | migration-aware-update tier-2 |
| migration-eval `migration-customized` fixture (diverged glossary/ROADMAP/rule) | Exercise transform-and-flag at depth (AC-2.6) — preserve customizations, never clobber | migration-aware-update tier-2 |
| migration-eval `migration-scale` fixture (dozens of concepts, multiple specs) | Completeness at scale — catch a missed file on a large repo | migration-aware-update tier-2 |
| migration-eval `migration-partial` fixture (half-hand-migrated tree) | Idempotent convergence (AC-4.4) on a partially migrated repo | migration-aware-update tier-2 |
| harness-agnostic live eval matrix: `codex exec` bootstrap e2e, migration eval, reviewer parity, self-host dogfood | Foundry's shippable bar (an eval per behavior change); deferred — the live `codex`/`claude` headless runs are slow and costly | harness-agnostic Wave 5 |
| harness-agnostic `knowledge.py` harness-aware skill-ref check (`.agents/skills/` alongside `.claude/skills/`) | Defensive completeness for a vendored `code` skill; the verbatim-template cost is not justified vs. its rarely-hit value (T12) | harness-agnostic Wave 3 |
| harness-agnostic Codex install how-to in `knowledge/releasing.md` (`codex plugin marketplace add`) | The manifests work live; only the doc is the gap (T7) | harness-agnostic Wave 5 |
