> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — knowledge-skill

## Summary

A `knowledge` skill that carries the **judgment** of maintaining the knowledge base — the layer
`code` Stage 5 has no skill to defer to. Today the lifecycle covers the *mechanism*
(`knowledge.py check` + `index`, append to `log.md`) but nothing tells the agent *where a fact
goes* (a glossary term vs. a concept file vs. a log entry vs. an `AGENTS.md` convention), which
OKF **type** a concept gets, how to record **provenance**, or how to keep the base **coherent**
(no orphans, stale claims, or contradictions). The skill encodes Google's **Open Knowledge
Format** (the base *is* an OKF bundle) plus Karpathy's **LLM-Wiki** maintenance discipline —
tightened for a single-repo engineering KB — and `code` Stage 5 defers to it, exactly as Stage 1
defers naming to `naming-standards`.

## Glossary impact

- No new canonical name. The skill operationalizes existing vocabulary — the OKF `type` taxonomy
  (`knowledge/README.md`), `Gate`, the `foundry-seed:` markers — and the `AGENTS.md`
  provenance/COE boundaries. "Home selection" is descriptive; no glossary row. Recorded in
  `knowledge/log.md`.

## US-1 — The knowledge skill

- AC-1.1 `plugins/foundry/skills/knowledge/SKILL.md` SHALL cover, within the ≤120-line budget:
  **home selection** (glossary term / concept file / `log.md` / `AGENTS.md` convention), the
  **four OKF types** (reference / architecture / guide / decision), **provenance** (search prior
  art before coining; a concept cites the code or spec it describes), **append-don't-overwrite**,
  and **coherence** (the orphan / stale / missing-page / contradiction checks).
- AC-1.2 THE skill SHALL be invocable — `name` + `description` frontmatter scoped to maintaining
  the knowledge base.
- AC-1.3 THE depth — the OKF format and the coherence checklist — SHALL live in `references/`,
  each reachable from `SKILL.md` (the skill is itself progressively disclosed: a lean entry +
  on-demand references).
- AC-1.4 THE skill SHALL teach **progressive disclosure** of the base: the read path `index.md`
  (catalog) → `knowledge.py outline <concept>` → `knowledge.py section <concept> <heading>` (read
  by slice, never full-load), and the maintainer's duty to keep `index.md` current and write a
  tight `description` + clear headings so the catalog and slice-navigation work.
- AC-1.5 `references/okf.md` SHALL document where Foundry **diverges from the OKF spec** —
  grounded in `knowledge.py` / `knowledge-config.json`: a fixed four-`type` set (unknown type
  fails the lint, vs. OKF's open/tolerant types), required `title`/`description`/`type` (vs. OKF's
  `type`-only), strict conformance, the `lifecycle` field for staleness (no OKF equivalent), and
  an append-only `log.md`.

## US-2 — The lifecycle defers to it

- AC-2.1 `code` Stage 5 (Knowledge) SHALL defer the placement-and-recording judgment to the
  `knowledge` skill (as Stage 1 lists `naming-standards`), keeping the stage a thin gate.

## US-3 — It routes (the eval)

- AC-3.1 THE `triggering` eval corpus SHALL gain `knowledge` (in `expect_values`) and a positive
  case — a knowledge-base-maintenance query routes to `knowledge` — proving discrimination via
  the existing `grade_triggering.py`.
- AC-3.2 A `keyword_trap` or `near_miss_negative` case SHALL guard the boundary (a query that
  merely mentions "knowledge" but is not KB maintenance does **not** route to the skill).

## Metrics

- A knowledge-base-maintenance query routes to `knowledge`; a near-miss does not — scored by
  `grade_triggering.py` (deterministic).
- The skill is within the ≤120-line budget and every `references/` file is reachable (the
  existing `check-context-budget.sh` / `check-skill-references.sh` gates).
