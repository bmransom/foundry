---
name: knowledge
description: Use when adding to or updating the knowledge base — placing a fact in its home (a glossary term, a concept file, a log entry, or an AGENTS.md convention), choosing its OKF type, recording provenance, and keeping the base coherent (no orphans, stale claims, or contradictions).
---

# Knowledge

The knowledge base is a Google **Open Knowledge Format** bundle — one concept per markdown file,
`type` frontmatter, a generated `index.md`, an append-only `log.md`, links as a graph. Maintain
it like Karpathy's LLM Wiki: the reading and thinking are easy; **the bookkeeping is the work.**
Foundry is stricter than OKF's "tolerate anything" — the glossary is a contract and `knowledge.py`
lints. Generic KB-maintenance practice; no glossary row.

## Where it goes — pick the home first

| The change is… | Home |
|---|---|
| a **canonical name** the repo should keep using | a row in `knowledge/glossary.md` (with provenance) |
| a durable **explanation, contract, how-to, or decision** | a **concept file** under `knowledge/` (pick the OKF type) |
| a standing **rule, boundary, or convention** | `AGENTS.md` (or `rules/`) |
| the **record** that something changed | a `knowledge/log.md` entry (append, newest-first) |

One fact often touches several — a new mechanism may add a concept, a glossary term, and a log
entry. (Choosing the *name* is `naming-standards`; choosing where it *lives* and recording it is
this skill.)

## The four OKF types (for a concept file)

- **reference** — evergreen lookup or contract (the glossary, the validation gates).
- **architecture** — how the system is built, and why.
- **guide** — a task-oriented how-to.
- **decision** — a dated record: a correction of error (COE), an experiment, an investigation.

## Provenance & anchoring

- Before coining a **canonical name**, search the prior art and record where it came from (the
  `AGENTS.md` boundary). Reuse the domain's term over an invented one.
- **Anchor** a claim to its source — cite the code, spec, or commit it describes, so a reader can
  check it and a future edit knows what it rests on.

## Append, don't overwrite

A re-touch **appends** — a `log.md` entry, or a new line in a concept's History — rather than
silently rewriting a claim. The log is the change record; a silent rewrite loses the *why*.

## Keep it coherent

Beyond `knowledge.py check` (frontmatter, mechanical) and `check-skill-references` (skill
orphans), check by judgment — the [`references/coherence.md`](references/coherence.md) lint:
**orphan** (a concept nothing links to), **stale** (a claim a newer source superseded),
**missing page** (an idea referenced often but with no file), **contradiction** (two files
disagreeing about the *same* concept — scoped: files sharing no concept can't contradict).

## Progressive disclosure

Read the base by **slice**, never by full-load: `index.md` (the catalog — one line per concept) →
`knowledge.py outline <concept>` (its heading tree) → `knowledge.py section <concept> <heading>`.
Keep that path working: run `knowledge.py index` after a change, write a tight one-line
`description`, and use clear headings — bad metadata breaks disclosure. Mark a superseded claim
`lifecycle: superseded` rather than deleting it — Foundry's staleness signal (OKF has none).

## Mechanics

Run `python3 scripts/knowledge.py check` and regenerate `python3 scripts/knowledge.py index`; add
the `log.md` entry; update `AGENTS.md` if a convention changed. The full OKF format — frontmatter,
the reserved files, links-as-graph, and **how Foundry diverges from OKF** — is in
[`references/okf.md`](references/okf.md).

## Traps

- Don't silently rewrite a claim — append, and record the *why*.
- Don't coin a canonical name with no provenance.
- Don't leave a concept orphaned, or a heavily-referenced idea without its own page.
- Don't put a repo's content into a Foundry template (mechanisms, not content).
