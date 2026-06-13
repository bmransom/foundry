# Navigation eval — tasks

**Status:** Spec — tasks drafted (2026-06-13) — tracked on the [board](../../docs/ROADMAP.md).

**Goal:** Build the nav-eval (arms, fixture, grader, driver), the reusable
correctness-vs-cost plotter, and token instrumentation across every eval — then run the
pilot to answer whether the disclosure protocol helps. Pure stdlib + the existing
headless harness; nothing shipped to consumers.

## Wave 1 — Foundations (no dependencies; parallel)

- [ ] T1: Author the fixture (independent ground truth) — `evals/fixtures/navigation/{tree/**, tasks.json, answer-key.json}`. Docs/specs at ≈100/500/2000 lines, each with a gold section and ≥1 near-duplicate decoy; `tasks.json` (id, question, doc); `answer-key.json` (gold_spans, correct_signature, decoys). Include ≥1 large-doc task with a decoy adjacent to the gold span — the discrimination self-check. [AC-1.2, 1.4, 1.5 · design §Data models, §Detection protocol]
- [ ] T2: Token helper — `evals/harness/eval_tokens.py`. Extract input+cache+output tokens from a `stream-json` log; stdlib; importable by every driver. [AC-3.1 · design §Context-recall & token measurement]
- [ ] T10: Glossary — `docs/glossary.md`. Add *arm*, *context recall*, *gold span*, *context cost* with prior-art provenance; *decoy* already present. [design §Glossary additions · naming rule]

## Wave 2 — Grader, plotter, token wiring (depends on Wave 1)

- [ ] T3: Grader — `evals/harness/grade_navigation.py` (deps T1, T2). Per (task, arm, run): success vs `answer-key`, context recall (gold lines loaded ÷ gold lines), decoy hit, tokens, tool-calls; emit `eval_case` + per-arm `summary`; mark a non-discriminating fixture rather than passing it. [AC-1.3, 1.6, 1.7 · design §Grader, §Error handling]
- [ ] T4: Plotter — `evals/harness/plot_cost_correctness.py` (dep: NDJSON schema, design §Data models). Read any eval's NDJSON → hand-emitted SVG: x = context tokens, y = correctness, one labelled point per arm, Pareto frontier marked; label missing cost. NDJSON-only, no grader code. [AC-2.1–2.4, 3.2 · design §Plotter, §Decisions]
- [ ] T6: Token capture in the existing drivers — `evals/harness/{reviewer-eval.sh, bootstrap-eval.sh, lifecycle-eval.sh}` (dep T2). Record `context_tokens` per run so the plotter serves every eval. [AC-2.2 · design §Token helper]

## Wave 3 — Driver (depends on Wave 2)

- [ ] T5: Driver — `evals/harness/navigation-eval.sh` (deps T1, T3). task × arm × N headless `claude -p … --output-format stream-json` in `tree/`; the three arm preambles (A0/A1/A2); save transcripts; call the grader; `--score-only` / `--grade-only` like the other drivers. [AC-1.1 · design §Driver, §Data flow]

## Wave 4 — Tests + gate (depends on the code)

- [ ] T7: Grader tests — `evals/harness/test_grade_navigation.py` (dep T3). Canned transcripts: gold-span load → recall 1; decoy answer → success 0 + decoy hit; no `ANSWER:` → protocol fail. [design §Testing strategy]
- [ ] T8: Plotter tests — `evals/harness/test_plot_cost_correctness.py` (dep T4). Canned NDJSON → SVG has the expected points + frontier; missing-token case handled. [design §Testing strategy]
- [ ] T9: Gate wiring — run T7 + T8 in the quick gate, mirroring how `test_score_review.py` runs today (deps T7, T8). Touches `scripts/check-fast.sh` and/or the `tests/` wrapper convention confirmed at implementation time. [design §Testing strategy]

## Wave 5 — Verification

- [ ] Run `scripts/check-fast.sh` → `check-fast: PASS`, including the two new test files.
- [ ] `navigation-eval.sh --grade-only` on a canned transcript → correct NDJSON (proves the pipeline without API).
- [ ] Generate SVGs for the nav-eval and ≥1 existing eval; eyeball axes + frontier.
- [ ] Pilot run `navigation-eval.sh 3` (needs `CLAUDE_CODE_OAUTH_TOKEN`); record the finding — including "not necessary" if that is the result — and the crossover, if any.
- [ ] Verify each AC against the result; move the board card Validating → Done with the recorded gate PASS.

## Traceability (AC → task)

| AC | Task(s) |
|---|---|
| 1.1 | T5 |
| 1.2 | T1, T3 |
| 1.3 | T3 |
| 1.4 | T1, T3 |
| 1.5 | T1 |
| 1.6 | T3 |
| 1.7 | T3 |
| 2.1–2.3 | T4 |
| 2.2 | T4, T6 |
| 2.4 | T4 |
| 3.1 | T2, T5 |
| 3.2 | T4 |

## Wave v2 — breadth sweep & hybrid (claimed @branch 2026-06-13)

- [x] `build_corpus.py` — N-doc corpus, gold in `gateway.md`, decoys + grep-noise filler — `evals/fixtures/navigation-breadth/`
- [x] breadth `tasks.json` (5 arms incl. hybrid + index) + `answer-key.json`
- [x] `grade_navigation.py --tag K=V` passthrough (corpus_size on every record)
- [x] `navigation-breadth-eval.sh` — corpus-size sweep driver
- [x] `plot_sweep.py` (content loaded vs corpus size) + `test_plot_sweep.py` + gate shim
- [x] live sweep N=1, sizes 5/25/100 → finding: native grep leanest at scale; docs.py catalog (`list`) is O(N), most expensive; disclosure not justified for greppable lookups. Untested: non-greppable / browse-by-topic queries (the regime where a catalog might earn its cost)
