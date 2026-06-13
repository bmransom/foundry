---
title: Docs index
description: How the docs are organized — the four kinds, the docs tool, the index.
kind: reference
---

<!-- foundry-seed: docs-readme v1 -->

# Docs

Browse by kind from the terminal: `python3 scripts/docs.py list`.
Or run the site: `cd knowledge && npm install && npm run dev`.

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

<!-- Add an index pointer here for every new doc. -->

- `glossary.md` — the ubiquitous language; the vocabulary contract.
- `validation.md` — every verification gate.
- `coe-template.md` — the correction-of-error template.

The board and roadmap live in `../roadmap/`: `ROADMAP.md` (the source of truth for
cross-spec status), `BACKLOG.md` (the idea pool), and per-feature specs in
`specs/` — see `../roadmap/specs/README.md` for the format.
