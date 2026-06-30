**Status:** In progress (2026-06-30) — tracked on the [board](../../ROADMAP.md).

# Loop-kickoff doctrine — absorb into foundry mechanisms

## Why

A standing implementation-loop block — review the spec for naming, domain, bounded contexts,
perf; default at the highest altitude; drive config through config objects; map a context
diagram; design tracer bullets; keep speccing when confidence is low — was re-pasted at every
kickoff. Foundry already mechanizes ~80% of it: the five-skill Spec consult, `code-review`
**Defaults**, the spec-format diagram + Metrics, the checkpoint Boundary, the `spec-review`
convergence loop. This card closes the three gaps; the paste retires and `code` carries the
doctrine.

## The three gaps

| Gap | Decision | Lands in |
|---|---|---|
| **Tracer bullets + confidence gate** — de-risk an open assumption before Build; low confidence is a spec signal, not a Build risk | Add to `code` §1 Spec; sharpen the Design gate | `skills/code/SKILL.md` |
| **Diagram locates the routine** — the context diagram places each stage of the routine and its per-context algorithm, not just the boxes | One sentence in the spec-format §Diagrams | `templates/seeds/roadmap/specs/README.md` (+ dogfood copy) |
| **Config objects** — code consumes config through explicit, per-context config objects | New `code-review` **Config** dimension + eval | `skills/code-review/` + `evals/fixtures/code-review/` |

## Config-object doctrine (the one opinionated stance)

Not "no env vars." Env vars (flags, files) **populate** a config object at the boundary; below
it, code consumes **explicit, typed config objects, decomposed per bounded context** — never an
ambient env read scattered through the call graph. Configs gain structure, per-context
ownership, and one place to validate that independent values agree. The **Config** dimension
flags: a raw env read below the boundary; a config bag passed whole into a context needing one
slice; independent values that must agree but are never checked together.

## Provenance (naming)

Established terms, no new coinage (prior-art Boundary): **context map** (Evans, *Domain-Driven
Design*), **tracer bullet** (Hunt & Thomas, *The Pragmatic Programmer*), **config object**
(common). No glossary debt.

## Metrics

- **Config dimension discriminates** — seed a raw-env-read-below-the-boundary defect in
  `evals/fixtures/code-review/tree/` + `answer-key.json`; the code-review eval must recall it
  (FLAGGED). The gate-discrimination proof the Boundary requires.
- Diagram + tracer-bullet wording is advisory, not a pass/fail gate — **N/A** for discrimination
  (nothing mechanical to seed). `lifecycle-eval` guards the `code` skill; `spec-review` and
  `code-review` already check diagram drift.

## Tasks (waves)

**Wave 1 — Draft A (advisory wording, no new behavior):**
1. `skills/code/SKILL.md` §1 Spec — add the de-risk paragraph (tracer bullets + confidence
   gate); amend the Design gate: open assumptions resolved or traced.
2. `templates/seeds/roadmap/specs/README.md` §Diagrams — add the locate-the-routine sentence;
   bump the seed marker `specs-readme v2 → v3`.
3. Mirror task 2 in the byte-identical dogfood copy `roadmap/specs/README.md`.

**Wave 2 — Draft B (new dimension, needs the eval):**
4. `skills/code-review/SKILL.md` + `references/dimensions.md` — add the **Config** dimension
   beside **Defaults**; add `config` to the skill description's dimension list.
5. `evals/fixtures/code-review/tree/` + `answer-key.json` — seed the config defect; run the eval
   to prove recall.

## Two judgment calls (Design gate)

1. **Draft A eval.** Advisory wording has nothing to discriminate; it ships under `lifecycle-eval`,
   not a new case. Accept, or require a structural assertion?
2. **Seed bump + dogfood sync.** Editing the `specs-readme` seed bumps `v2 → v3` (so `update`
   propagates) and its byte-identical dogfood copy. A seed refresh, not a convention break — no
   migration playbook or `conventionVersion` bump. Agree?
