# OKF alignment — tasks

**Status:** Validating (2026-06-16) — tracked on the [board](../../ROADMAP.md).
The board is authoritative. The implementation has moved past these build-order
boxes; remaining validation is the full bootstrap/reviewer eval confirmation.

**Atomic migration.** All waves land in **one commit**; intermediate states break `knowledge check` and byte-identity, so the gate is run only at Wave 7. Waves are build order + dependency, not separately committable. Within a wave, tasks on different files run in parallel. Every verbatim edit touches **both trees** (`scripts/…` + `plugins/foundry/templates/verbatim/…`) byte-identically; every seed edit touches the seed under `plugins/foundry/templates/seeds/…` and foundry's own copy.

### Wave 0: Setup
- [ ] T0: Claim the `okf-alignment` card on the board — `roadmap/ROADMAP.md`

### Wave 1: Renames (git mv, both trees)  (no deps)
- [ ] T1: `docs.py`→`knowledge.py` — `scripts/knowledge.py` + `plugins/foundry/templates/verbatim/scripts/knowledge.py`
- [ ] T2: `test_docs.py`→`test_knowledge.py` — `scripts/test_knowledge.py` + verbatim twin
- [ ] T3 (D1): `docs-config.json`→`knowledge-config.json` — `knowledge/knowledge-config.json` + seed twin
- [ ] T4: `docs-conventions.md`→`knowledge-conventions.md` — `.claude/rules/knowledge-conventions.md` + seed twin

### Wave 2: Tool + config + tests  (depends on Wave 1)
- [ ] T5: marker `foundry-template: knowledge v1`; read `type` (not `kind`) and config keys `types`/`concept_globs`/`reserved_files`; add `index` subcommand; `check` gains the index-freshness assertion; relabel output to "concept(s)" — `scripts/knowledge.py` + verbatim twin *(byte-identical)*. AC-1.1/1.2/1.3/1.5/2.1, D2
- [ ] T6 (D1): keys `kinds`→`types`, `doc_globs`→`concept_globs`; `required_fields:[title,description,type]`; `reserved_files:[knowledge/index.md,knowledge/log.md]` — `knowledge/knowledge-config.json` + seed. AC-1.3/1.5
- [ ] T7: cases use `type`; add reserved-file, enum, and index-freshness cases — `scripts/test_knowledge.py` + verbatim twin. AC-1.2/1.3/1.5/4.2

### Wave 3: Concept content  (depends on Wave 2)
- [ ] T8: flip `kind:`→`type:` — `knowledge/{glossary,validation,coe-template,releasing,README}.md`. AC-1.1
- [ ] T9: flip `kind:`→`type:` — `plugins/foundry/templates/seeds/knowledge/{glossary,validation,coe-template,README}.md`. AC-1.1/4.1
- [ ] T10 (D3): confirm `README.md` is an ordinary concept (`type: reference`, not reserved) so it lints + lists — covered by T6 `reserved_files` + T8/T9. AC-1.4 *(superseded by `okf-listing-fidelity`: `README.md` is now reserved — it was `srcExclude`d yet listed → a dead link.)*
- [ ] T11 (D2): regenerate the OKF listing (no frontmatter) via `knowledge.py index` — `knowledge/index.md` + seed. AC-1.4 *(amended by `okf-listing-fidelity`: the listing now carries an `okf_version` frontmatter.)*
- [ ] T12: add OKF §7 change log (no frontmatter; `## YYYY-MM-DD`, newest first) — `knowledge/log.md` + seed. AC-3.1

### Wave 4: Rules, glossary, roadmap strip  (depends on Wave 1; parallel with Wave 3)
- [ ] T13: vocabulary→knowledge/concept/type; combine `## Names and prose`; cite `log.md`; keep `paths: knowledge/**` — `.claude/rules/knowledge-conventions.md` + seed. AC-2.2/2.3/3.2
- [ ] T14: combine `## Names`/`## Prose`→`## Names and prose` — `.claude/rules/spec-conventions.md` + seed. AC-2.3
- [ ] T15: add `Concept` + `type` terms (OKF provenance); retire "doc" framing in the description — `knowledge/glossary.md` + seed. AC-2.2
- [ ] T16: strip vestigial `kind: reference` (keep `foundry-seed:` markers) — `roadmap/{ROADMAP,BACKLOG}.md`, `roadmap/specs/README.md`, seed `roadmap/{ROADMAP,BACKLOG}.md` + seed `roadmap/specs/README.md` + seed `features/README.md`. AC-1.6

### Wave 5: Wiring — gate, skills, prose  (depends on Waves 1–2)
- [ ] T17: gate step `docs check`→`knowledge check`, label `== docs`→`== knowledge` — `scripts/check-fast.sh`. AC-2.1/4.4
- [ ] T18: `docs.py`→`knowledge.py`, "docs tool"→"knowledge tool", doc→concept, manifest template name, the "Docs build…under knowledge/" row — `AGENTS.md`, `plugins/foundry/skills/bootstrap/references/{generate,verify}.md`, `plugins/foundry/skills/code/SKILL.md`, `knowledge/{validation,README}.md` + seed README. AC-2.1/2.2
- [ ] T19: `docs.py`→`knowledge.py` references — `roadmap/specs/foundry-core/*.md`, `roadmap/specs/navigation-eval/*.md`, `roadmap/ROADMAP.md`. AC-2.2

### Wave 6: Evals  (depends on Waves 1–3)
- [ ] T20: verbatim `scripts/docs.py`→`knowledge.py`, template `docs`→`knowledge`, config filename, add `knowledge/log.md` (seed) — `evals/harness/grade.py` is schema-driven; edit `evals/fixtures/{rust-cli,python-service,ts-monorepo}/expectations.json` + `evals/harness/wclip-smoke-expectations.json`. AC-4.1
- [ ] T21: `build_complete_tree` + `BASE_EXPECTATIONS`: `scripts/knowledge.py`, template `knowledge`, config filename, marker — `evals/harness/test_grade.py`. AC-2.1/4.1
- [ ] T22: generators emit `type` frontmatter + write `knowledge-config.json` (`concept_globs`/`types`) + drop `knowledge.py`; update tool refs — `evals/fixtures/navigation/build_tree.py`, `evals/fixtures/navigation-breadth/build_corpus.py`, their `tasks.json`/`answer-key.json`, `evals/harness/{grade_navigation,test_grade_navigation}.py`. AC-4.1
- [ ] T23: finding label `"kind":`→`"type":` (scorer unchanged) — `evals/fixtures/reviewer/answer-key.json`, `evals/harness/test_score_review.py`. AC-4.3
- [ ] T24: defect fixture `kind: guide`→`type: guide` — `evals/fixtures/python-service/defects/debt-term/knowledge/launch-notes.md`. AC-1.1/4.1

### Wave 7: Verification
- [ ] T25: `scripts/check-fast.sh` → exit 0 (byte-identity, knowledge check, context-budget, all script tests). AC-4.4/4.2
- [ ] T26: `evals/harness/bootstrap-eval.sh python-service` → PASS (knowledge.py, `knowledge/log.md`, `type` concepts present). AC-4.1
- [ ] T27: `evals/harness/reviewer-eval.sh` → PASS (type labels). AC-4.3
- [ ] T28: grep assertion — no `roadmap/**` or `features/**` file carries `kind`/`type`. AC-1.6
- [ ] T29: grep assertion — `docs.py` / "the docs tool" no longer name the tool/unit/collection. AC-2.2
- [ ] T30: manually verify each acceptance criterion in `requirements.md`.

## AC coverage

| AC | Tasks | | AC | Tasks |
|---|---|---|---|---|
| 1.1 | T5,T8,T9,T24 | | 2.2 | T13,T15,T18,T19,T29 |
| 1.2 | T5,T7 | | 2.3 | T4,T13,T14 |
| 1.3 | T5,T6,T7 | | 3.1 | T12 |
| 1.4 | T5,T10,T11 | | 3.2 | T13 |
| 1.5 | T5,T6,T7 | | 4.1 | T20,T21,T22,T24,T26 |
| 1.6 | T16,T28 | | 4.2 | T5,T7,T25 |
| 2.1 | T1,T5,T6,T17,T18,T20,T21 | | 4.3 | T23,T27 |
| | | | 4.4 | T17,T25 |
