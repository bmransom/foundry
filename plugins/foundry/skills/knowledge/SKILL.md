---
name: knowledge
description: Use when adding to or updating the knowledge base — placing a fact in its home (a glossary term, a concept file, a log entry, or an AGENTS.md convention), choosing its OKF type, recording provenance, and keeping the base coherent (no orphans, stale claims, or contradictions). The interactive knowledge-stage skill; grades against the same rubric the driver's knowledge gate uses.
---

# Knowledge

The knowledge base is an Open Knowledge Format bundle — one concept per markdown file, `type`
frontmatter, a generated `index.md`, an append-only `log.md`, links as a graph. The reading
is easy; **the bookkeeping is the work.** The glossary is a contract, and `knowledge.py`
lints it.

## The judgment is the knowledge rubric — fetch it

```
.foundry/bin/foundry rubric knowledge
```

Fetch it and follow it: choose the fact's home (glossary term / concept file / `log.md` entry
/ AGENTS.md convention), its OKF `type`, and record provenance for any coined canonical name.
Keep the base coherent — no orphaned concepts, stale claims, or contradictions with the
glossary.

## Mechanics

```
python3 scripts/knowledge.py check      # frontmatter + glossary lint (also in the gate)
python3 scripts/knowledge.py index      # regenerate the reserved index.md after any change
```

Append the change to `knowledge/log.md` (newest first), and update `AGENTS.md` if a
convention changed. The gate's knowledge check must be clean before Finish.

## Common mistakes

- Do not hand-edit `index.md` — it is generated; regenerate it.
- Do not coin a canonical name without recording its prior art in the glossary.
- Do not leave a concept unlinked or a superseded claim standing.
- Do not re-derive judgment here; if the rubric is wrong, fix `src/foundry/rubrics/knowledge.md`.
