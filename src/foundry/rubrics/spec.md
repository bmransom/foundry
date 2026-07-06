# Spec stage rubric

Author or refine `roadmap/specs/<feature>/{requirements,design,tasks}.md` to the repo's
spec format (`roadmap/specs/README.md`) in the vocabulary of `knowledge/glossary.md`, then
review it until no blocking finding remains.

## Intent

Turn the work into a spec a builder can execute without guessing: testable requirements,
a design that names its public surface and invariants, and a task plan. De-risk on paper
— an assumption you cannot settle (an algorithm's feasibility, an interface's fit, a
performance ceiling) is a spec signal, not a build risk: keep speccing, or carry it as an
open question, never absorb it into build.

## Invariants

- `requirements.md` states user stories with EARS acceptance criteria — one testable
  behavior per criterion.
- `design.md` declares a **Public surface** section, designed **structs before
  interfaces**: first the data structures with their fields and per-field invariants, then
  the interfaces over them — signatures, protocols or traits, wire formats, and config
  keys. Data shapes drive the operations, not the reverse. A missing section is a blocking
  finding.
- `design.md` declares an **Invariants** section: the properties that must always hold. A
  missing section is a blocking finding.
- `design.md` names the metrics that tell whether the feature works, or states **N/A**
  with a one-line reason; it carries a Mermaid architecture or component diagram — how the
  structs and interfaces compose — and a **class diagram that persists the public
  surface**: every struct (with its fields) and interface it declared. A typed surface
  whose structs or interfaces are absent from the class diagram is a blocking finding; a
  shell-only component with no typed structure uses architecture plus data-flow instead.
- `tasks.md` is ordered in waves; each task is TDD (its test lands red first) and names
  the gate that proves it.
- Names match the glossary's canonical terms and entity model; a new canonical name
  carries its prior-art provenance.
- Prose meets the repo's writing style: no needless words, active voice, definite
  assertions.

## Severity

A **contract violation** is blocking: a wrong canonical name, a debt term used for its
concept, an entity-model conflict, missing provenance, a spec-format breach, a missing
**Public surface** or **Invariants** section, or an internal inconsistency. A taste-level
prose preference is advisory. Objective banned filler is the prose linter's job, not a
finding here.

## Open questions

Every public-surface or invariant decision the spec cannot resolve becomes an
`open_questions` entry — never a silent assumption. Each entry names its `topic`
(`surface` or `invariant`) and the `question` in one line.

## Output contract

Emit a fenced JSON block carrying the open questions, then the verdict as the **last
line**. The JSON shape:

```json
{"open_questions": [{"topic": "surface", "question": "..."}]}
```

Use `{"open_questions": []}` when none remain. The last line is exactly one of:

- `SPEC_REVIEW: CLEAN` — no unresolved blocking finding remains (advisory may remain).
- `SPEC_REVIEW: FINDINGS` — one or more blocking findings, listed above the JSON block.
