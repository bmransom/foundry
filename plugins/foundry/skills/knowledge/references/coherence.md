# Coherence checks

Karpathy's LLM-Wiki insight: a knowledge base rots from **confident-but-stale** memory and silent
contradictions, and the tedious part of preventing that is bookkeeping. The mechanical gates catch
frontmatter (`knowledge.py check`) and skill-reference orphans (`check-skill-references.sh`); the
rest is judgment — run these when adding or changing a concept (the [`knowledge`](../SKILL.md) skill).

| Check | What it is | How to look / fix |
|---|---|---|
| **orphan** | a concept no other file links to | grep for inbound links; none → link it from a related concept or `index.md`, or fold it in |
| **stale claim** | a claim a newer source superseded | update the concept + append a History line; mark the old one `lifecycle: superseded` — don't leave two live claims |
| **missing page** | an idea referenced often but with no file of its own | if several files lean on a concept that has no page, give it one |
| **contradiction** | two files disagreeing about the **same** concept | *scoped* — files sharing no concept can't contradict; check a concept's pages against each other and the source |
| **missing cross-reference** | related concepts not linked | link concepts that reference each other, so the graph (not just the folder) carries the relationships |

**Append, don't overwrite** — a re-touch adds to `log.md` / a History section so the *why*
survives. **Scope the contradiction check** (Karpathy) — two claims can only contradict if they
are about the same concept, so a review touches the changed concept's neighbours, not the whole base.

These are judgment for now. A future deterministic knowledge-lint could mechanize the structural
checks (orphans, missing pages) — the gate-not-prose principle — but contradiction and staleness
detection stay judgment-heavy.
