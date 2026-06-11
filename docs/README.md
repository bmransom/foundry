---
title: Docs index
description: How foundry's docs are organized — the four kinds, the docs tool, the index.
kind: reference
---

<!-- foundry-seed: docs-readme v1 -->

# Foundry docs

Browse by kind from the terminal: `python3 scripts/docs.py list`.
Or run the site: `cd docs && npm install && npm run dev`.

## The four kinds

Every doc carries frontmatter — `title`, `description`, and one `kind`:

- **reference** — evergreen lookup and contracts (the glossary, the validation gates).
- **architecture** — how the system is built, and why.
- **guide** — task-oriented how-tos.
- **decision** — dated engineering records: corrections of error, experiment
  plans, investigations.

## The docs tool

- `python3 scripts/docs.py list` — curated docs, grouped by kind.
- `python3 scripts/docs.py outline <doc>` — one doc's heading tree.
- `python3 scripts/docs.py section <doc> <heading>` — print one section.
- `python3 scripts/docs.py check` — lint frontmatter; runs in the quick gate.

## Index

Add an index pointer here for every new doc.

- `ROADMAP.md` — the board; the single source of truth for cross-spec status.
- `BACKLOG.md` — the idea pool.
- `glossary.md` — foundry's vocabulary contract.
- `validation.md` — foundry's verification gates.

Per-feature requirements, design, and tasks live in `../specs/`; see `../specs/README.md` for the format.
