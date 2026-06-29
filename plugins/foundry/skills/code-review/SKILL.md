---
name: code-review
description: Use when reviewing an implementation diff against its spec before Finish — grading lifecycle evidence, complete implementation, docs sync, domain language, logging, simplicity, interfaces, structure, efficiency, defaults, and test discrimination from artifacts, never self-claims.
---

# Code Review

Review a change against its spec and the repo contract. Read-only: return findings,
never edit the consumer repo. Prefer fresh context so the reviewer sees the code, not the author's rationale.

**Provenance.** Code review is generic industry practice, not a coined Foundry
concept; the `spec-review` sibling has no glossary row, so `code-review` adds none.
It reuses the glossary's existing vocabulary — Gate, Wide event, Seeded defect,
Decoy, Fixture, Card / Board, Consumer repo, Harness. `spec-review` reviews
context-resident prose; `code-review` reviews the implementation diff against it.

## Fresh-context workflow

1. Identify the spec dir and the diff range (`git merge-base main HEAD`..HEAD by
   default).
2. Run `scripts/spawn-code-reviewer.sh <spec-dir> [project-dir]` when tmux is
   available. The wrapper delegates to Foundry's shared fresh-session runner and,
   on a multi-family manifest, runs the cross-model refuter pass.
3. Wait for the report in `.foundry/reports/code-review/`.
4. Read the report. Fix every blocking finding and re-review **blind** — never hand the
   reviewer a summary of what you changed; a docs or knowledge gap loops back to Knowledge first.

If fresh context is unavailable, say so and hold the gate — never substitute a primed inline
re-pass for an independent review.

The runner converges automatically — re-review → union → refuter once — and the
lifecycle drives fix → re-review. See
[`references/convergence.md`](references/convergence.md) for the inner/outer loop
mechanics: union by normalized signature, two consecutive no-new passes, the 20-pass
and 20-round caps, and escalation.

## Contract

Read these before reviewing; grade every dimension from what you read or run:

- `knowledge/glossary.md` — canonical terms, debt terms, entity model.
- The `AGENTS.md` contract — Boundaries, Commands, Writing style.
- `roadmap/ROADMAP.md` and `knowledge/validation.md` — board card state and the
  recorded gate PASS (lifecycle evidence; never trust an author's gate claim).
- `requirements.md`/`design.md`/`tasks.md` — the spec under review.

If a contract file is missing, note that and review against the contract that exists.

## Dimensions

Grade these from artifacts you read or commands you run — never from self-claims.
The full grading table, evidence sources, and size tripwires live in
[`references/dimensions.md`](references/dimensions.md):

- **Lifecycle evidence** — spec, diff, board, `validation.md`; the recorded gate
  decides.
- **Complete implementation** — build an **AC → Scenario → test → code** matrix;
  flag any AC with no implementing artifact. Mechanical artifacts are the coverage
  signal; keyword-mapping an AC to changed code is not coverage.
- **Docs sync** — RUN `python3 scripts/knowledge.py check` yourself; verify each
  `design.md` architecture/class diagram against the shipped components and flag a
  drifted diagram; flag a `design.md` with no Metrics section and no N/A.
- **Domain language** — flag a glossary debt term used outside its `Replaces`
  column, or a coined name with no provenance.
- **Logging consistency** — flag a production path mixing a raw
  `print`/`console.log`/`echo` with the **Wide event** for one unit of work; a CLI
  surface like `print --help` is legitimate.
- **Simplicity** and **clean interfaces** — flag needless abstraction, speculative
  config, or a rewrite outside spec scope.
- **Modular structure** — size tripwires are **advisory** (new > 400, touched >
  800, +250 growth, function > 80 LOC; exclude generated/vendor/tests); a tripwire
  alone never fails.
- **Performance / efficiency** — flag a hot-path algorithmic regression, redundant
  IO/model/tool calls, or hoistable per-item work; a hot-path regression blocks, a
  cold-path tuning opportunity is advisory (grounded in the `performance` skill).
- **Sensible defaults** — flag footgun defaults or unexplained magic values.
- **Robust tests** — flag a test that does not **discriminate** a seeded defect,
  exercises only a fake or the happy path, or omits failure/edge cases.

## Calibration

Precision first — a false positive gets the reviewer ignored. Cite a `file:line` you read or
**drop the finding**; **silence beats noise** (zero findings is fine); cluster; read callers/callees,
not just the hunk; leave style to the linter; set severity by verifiability. Ground findings in
the spec — grade against its ACs, never invent a requirement, treat your fix as a hypothesis. See [`references/dimensions.md`](references/dimensions.md).

## Output contract

Write the full report to the report path and print it. The report tail carries
three parts in order:

1. The findings body — each finding states its **severity**, **dimension**,
   **file:line**, **evidence**, **problem**, and a concrete **fix**.
2. A `FLAGGED:` footer — one `FLAGGED: <flagged signature>` line per flagged
   finding, after the body and before the verdict. A complete-implementation
   finding's signature is the unimplemented AC id, e.g. `AC-2.1`.
3. A single verdict line, last: `CODE_REVIEW: PASS` or `CODE_REVIEW: FAIL`.

Severity is the gate, not finding count. A **blocking** finding fails the verdict
and prohibits Finish: emit `CODE_REVIEW: FAIL` whenever an unresolved blocking
finding exists. Emit `CODE_REVIEW: PASS` when every finding is advisory or
resolved. The footer matches `score_review.py` exactly, so the eval scores it
unchanged.

## Cross-model refuter

After the candidate footer, a fresh-context **refuter** runs on a **different
harness family**, read-only, to drop the reviewer's false positives. It is a
**single asymmetric** pass — not a symmetric debate or multi-round argument:

- Context-isolated: it sees ONLY the candidate `FLAGGED:` findings and the
  diff/artifact, never the reviewer's reasoning.
- Per finding, KEEP only with concrete evidence the finding is real, else **DROP**.
- **DROP-only**: it may only REMOVE a `FLAGGED:` finding, never ADD one
  (recall-monotone-down, precision-up).
- One harness family only → skip the refuter; run the reviewer single-agent.

The refuter is enabled by default only after the A/B eval proves it holds mean
recall ≥ 4/5 and zero decoy hits. See [`references/dimensions.md`](references/dimensions.md).
