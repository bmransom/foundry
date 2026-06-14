# Navigation eval — design

**Status:** Spec — design drafted (2026-06-13) — tracked on the [board](../../ROADMAP.md).

## Architecture overview

The nav-eval is a fourth Layer-3 eval beside reviewer / bootstrap / lifecycle, in
`evals/harness/` with a fixture under `evals/fixtures/navigation/`. It reuses the
established shape: a bash driver runs headless `claude` over a fixture N times per arm; a
stdlib Python grader scores the saved transcripts against an independent answer key and
emits NDJSON; a separate stdlib plotter turns any eval's NDJSON into a
correctness-vs-cost chart.

## Constraints

- **No consumer dependencies.** The harness and plotter live in `evals/`, which bootstrap
  never installs — so they add nothing downstream. Any versioning foundry later ships to
  consumers stays commit-level and tool-agnostic (Conventional Commits, semver, `vX.Y.Z`
  tags), never a specific release tool such as release-please.
- **Zero-dependency tooling.** Stdlib Python + bash only, like `knowledge.py`/`grade.py`. The
  plotter emits SVG by hand rather than importing matplotlib.
- **Independent oracle.** The grader shares no code with any arm; ground truth is an
  independently authored `answer-key.json`.

## Components

| Component | Location | Purpose |
|---|---|---|
| Driver | `evals/harness/navigation-eval.sh` | run each task × arm × N headless; save transcript; call grader; `--score-only`/`--grade-only` like the others |
| Grader | `evals/harness/grade_navigation.py` | from each transcript: success vs key, context recall, decoy hit, tokens, tool-calls; emit NDJSON |
| Token helper | `evals/harness/eval_tokens.py` | extract token usage from a stream-json log; shared so every driver can record cost (US-3) |
| Plotter | `evals/harness/plot_cost_correctness.py` | read any eval's NDJSON → SVG scatter + Pareto frontier |
| Grader tests | `evals/harness/test_grade_navigation.py` | grade canned transcripts (stdlib `unittest`) |
| Plotter tests | `evals/harness/test_plot_cost_correctness.py` | SVG from canned NDJSON; missing-token case |
| Fixture | `evals/fixtures/navigation/` | `tree/` (knowledge docs at ≈100/500/2000 lines w/ gold + decoy sections), `tasks.json`, `answer-key.json` |

## The arms — making an approach comparable

An **arm** is a navigation instruction prepended to the task prompt; the same task runs
under each. Arms are prompt preambles, not tool gates: `claude -p` cannot hard-gate
native `Read`, so we measure behavior, not assume it. The prompt sets the arm, the
transcript reveals what the agent did, and the grader measures outcomes regardless of
compliance — so the eval reports the realistic effect of *instructing* an approach, not
an idealized one.

| Arm | Prompt preamble |
|---|---|
| A0 full-load | "Read each relevant file in full before answering." |
| A1 native | "Use `Read` and `Grep` to find what you need; do not use `knowledge.py`." |
| A2 disclosure | "Use `knowledge.py outline <doc>` then `knowledge.py section <doc> <heading>`; read short files whole." |

## Data flow

1. Driver loads `tasks.json`. For each (task, arm, run): prompt = arm preamble + task;
   run `claude -p … --output-format stream-json` in `tree/`; save `…run<i>.log`.
2. Grader reads each transcript: the final `ANSWER:` line (success vs key, decoy hit);
   `tool_use` events (files/ranges/sections loaded → context recall; tool-call count);
   the result `usage` (context tokens).
3. Grader emits one `eval_case` per (task, arm, run) and one `summary` per arm.
4. Plotter reads the NDJSON → one SVG per eval: x = context tokens, y = correctness, a
   labelled point per arm, Pareto frontier marked.

## Detection protocol

Like reviewer-eval's FLAGGED footer: the task prompt requires the agent to end with
`ANSWER: <value>`. The grader matches it (case-insensitive) against the key's
`correct_signature` (success) and `decoys[].signature` (decoy hit). No `ANSWER:` line →
the run scores zero success, recorded as a protocol fail — never silently.

## Data models

`answer-key.json` (independent ground truth):

```json
{ "fixture": "navigation",
  "tasks": [
    { "id": "T1", "question": "...", "doc": "knowledge/large.md",
      "gold_spans": [{ "file": "knowledge/large.md", "heading": "Retry policy" }],
      "correct_signature": "5 attempts",
      "decoys": [{ "id": "D1", "signature": "3 attempts" }] } ] }
```

NDJSON `eval_case` (existing schema + the metrics fields):

```json
{ "event": "eval_case", "fixture": "navigation", "task": "T1", "arm": "A2", "run": 1,
  "verdict": "pass", "success": true, "context_recall": 1.0, "context_tokens": 4120,
  "tool_calls": 3, "decoy_hit": false, "detail": "..." }
```

`summary` (per arm): `mean_success`, `mean_recall`, `mean_context_tokens`, `decoy_hits`,
`runs`, `verdict`. The plotter's input contract is any record carrying a correctness
scalar + `context_tokens`; existing evals map their metric (recall, pass-rate) to the y
value via a one-line adapter.

## Context-recall & token measurement

Both come from the transcript the harness already saves — the agent is untouched.
`tool_use` events give the file + range (`Read` offset/limit), the `Grep`, or the
`knowledge.py section/outline` call → the loaded span; recall = gold lines covered ÷ gold
lines needed. Tokens come from the result record's `usage` (input + cache + output) via
the shared `eval_tokens.py`, which is also wired into the reviewer/bootstrap/lifecycle
drivers so the plotter produces a chart for every eval (AC-2.2).

## Error handling / failure modes

- Empty or garbled transcript → run scores zero success, recall 0 — recorded, no crash.
- No `ANSWER:` line → protocol fail (zero success), recorded.
- `claude -p` nonzero exit → that run's `eval_case` is a fail.
- **Non-discriminating fixture (AC-1.7):** if across all runs no arm ever fails and no
  decoy is ever hit, the summary marks the fixture non-discriminating — a vacuous eval,
  not a pass (the seeded-defect/discrimination rule).
- Missing token usage (pre-instrumentation results) → plotter labels cost missing and
  plots correctness only (AC-3.2); never fabricated.

## Testing strategy (independent oracle)

The arms are the system under test; the oracle is the independently authored
`answer-key.json` plus a grader sharing no code with any arm. Beyond that:

- `test_grade_navigation.py` on canned transcripts: one that loads the gold span scores
  recall 1; one that answers a decoy scores success 0 + decoy hit; one with no `ANSWER:`
  scores a protocol fail.
- `test_plot_cost_correctness.py`: canned NDJSON → SVG contains the expected points and
  frontier; the missing-token case is handled.
- Discrimination self-check: the fixture must contain at least one large-doc task where a
  decoy sits near the gold span, so full-load and disclosure can plausibly diverge — else
  the eval cannot discriminate.
- Both test files wire into `check-fast.sh` script tests (like `test_score_review.py`), so
  the eval tooling is itself gated.

## Performance / cost

Headless runs dominate: tasks × arms × N × minutes. v1 stays small — ≈3 tasks × 3 arms ×
3 runs ≈ 27 calls, a smoke alarm, not statistics. `--score-only`/`--grade-only` re-score
without re-running. The size sweep (AC-1.5) is a few tasks of varied size, not a full
matrix.

## Glossary additions (prior-art provenance)

Recorded in `knowledge/glossary.md`: **arm** (experimental design / A-B testing); **context
recall** (RAG eval / RAGAS); **gold span** (IR ground truth); **context cost** (= context
tokens loaded). *Decoy* already exists in the reviewer fixture and is reused.

## Decisions

- **Viz = hand-emitted SVG.** Zero-dependency, embeds in the vitepress site, commits
  cleanly. Rejected: matplotlib (a dependency), Vega-Lite-in-docs (doc-site coupling).
- **Arm = prompt preamble, not hard tool-gating.** Measures the realistic effect of
  instructing an approach; the transcript records actual behavior.
- **Plotter is eval-agnostic** (NDJSON-only, AC-2.4), so it serves every eval once each
  records `context_tokens`.

## AC traceability

| AC | Satisfied by |
|---|---|
| 1.1 | Driver: task × arm × N loop |
| 1.2 | Independent `answer-key.json` + grader (no shared code) |
| 1.3 | Grader: success, recall, tokens, tool-calls per run |
| 1.4 | `answer-key.json` decoys + decoy-hit scoring |
| 1.5 | Fixture: ≈100/500/2000-line docs |
| 1.6 | NDJSON `eval_case`/`summary`, existing schema |
| 1.7 | Non-discriminating check in the summary |
| 2.1–2.3 | Plotter: SVG, per-arm points, Pareto frontier |
| 2.4 | Plotter reads NDJSON only |
| 3.1 | `eval_tokens.py` from stream-json, wired into every driver |
| 3.2 | Plotter labels missing cost |

## v2 — breadth & hybrid (corpus-size sweep)

The depth pilot showed native Read/Grep already navigates a *known* doc leanly, so
disclosure showed no benefit there. The open question is **breadth**: as the corpus grows
and the agent must discover *which* doc holds the answer, does structure-aware navigation
overtake grep?

- **Breadth fixture** (`evals/fixtures/navigation-breadth/`, via `build_corpus.py`): N docs
  where the answer lives only in `gateway.md`; `staging.md`/`edge.md` are decoys; filler
  docs each mention `timeout` benignly so `grep -r timeout` returns ~N hits — the noise
  that scales. Each doc carries frontmatter, so `knowledge.py list` is a real catalog. Tasks
  never name the target doc, so discovery cost is real.
- **Five arms**: `full-load`, `native` (grep/read), `disclosure` (catalog→section),
  **`hybrid`** (grep-locate scoped via `knowledge.py list --paths`, then `section`), `index`
  (`knowledge.py list` by description → `section`).
- **Sweep**: `navigation-breadth-eval.sh` rebuilds the corpus per size, runs every arm, and
  grades with `--tag corpus_size=N`. `plot_sweep.py` draws content-loaded vs corpus size,
  one line per arm — the crossover answers "how large must the corpus be."
- **Hybrid uses existing tools only.** A dedicated `knowledge.py search` subcommand is
  deliberately *not* built yet — the eval must first show the hybrid wins and that the
  multi-call ergonomics cost something. Measure, then build.
