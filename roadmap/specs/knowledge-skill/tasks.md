> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — knowledge-skill

## Wave 1 — the skill

- T1 `plugins/foundry/skills/knowledge/SKILL.md`: the guidance — **home selection** (glossary
  term / concept file / `log.md` / `AGENTS.md` convention), the **four OKF types**, **provenance
  + anchoring**, **append-don't-overwrite**, **coherence** (orphan / stale / missing-page /
  contradiction), and the mechanics (`knowledge.py check`/`index`, log the change) — within the
  ≤120-line budget; `name`/`description` frontmatter (AC-1.1, AC-1.2).
- T2 `plugins/foundry/skills/knowledge/references/okf.md` + `coherence.md`: the OKF format + type
  taxonomy (one concept/file, frontmatter, `index.md`/`log.md`, links-as-graph), and the
  Karpathy coherence checks with how to run each; both linked from `SKILL.md` (AC-1.3).
- Gate: `check-context-budget.sh` (≤120) + `check-skill-references.sh` (references reachable).

## Wave 2 — wire into the lifecycle

- T3 `plugins/foundry/skills/code/SKILL.md`: Stage 5 (Knowledge) names the `knowledge` skill for
  the placement-and-recording judgment, one line, as Stage 1 names `naming-standards` — keep the
  stage within budget (AC-2.1).
- Gate: `code` SKILL.md within budget; `knowledge.py check` clean.

## Wave 3 — the eval + knowledge

- T4 `evals/fixtures/triggering/cases.json`: add `knowledge` to `expect_values` + a **positive**
  case (a KB-maintenance query → `knowledge`) + a **near-miss / keyword_trap** (mentions
  "knowledge" but is not KB maintenance → not the skill). Close the pre-existing `debug` gap
  properly: add `debug` to `expect_values` **with a positive case** (`expect_values` alone is
  untested — `grade_triggering.py` scores only `cases`). Refresh the corpus `note` (its "12
  skills" count is stale). The grader scores the discrimination (AC-3.1, AC-3.2).
- T5 `knowledge/log.md`: record the skill; confirm no glossary row needed.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; the `triggering` corpus stays
  discriminating (its grader rejects a non-discriminating corpus).
