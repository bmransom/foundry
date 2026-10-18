---
title: Spec format
description: How specs are written — requirements, design, and tasks per feature.
---

<!-- foundry-seed: specs-readme v6 -->

# Specs

A feature's spec is `roadmap/specs/<feature>/` with three files:

- `requirements.md` — user stories with EARS acceptance criteria.
- `design.md` — decisions, architecture, rationale.
- `tasks.md` — the implementation plan, ordered in waves.

## Proportion

Size the spec to the risk. A public surface, wire format, invariant, or irreversible
migration earns full rigor; an internal helper earns a sentence. A change too small for a
spec — a bug fix, a contained refactor — needs none: its test and its commit message carry
it. State each fact once and link to it.

## Status header

Every spec file opens with a status header that points to the board:

> **Status:** Ready (2026-01-15) — tracked on the [board](../ROADMAP.md).

When a spec and the board disagree, the board wins.

Use the board's status taxonomy.

## EARS acceptance criteria

Write each criterion in EARS form — `WHEN <trigger>, THE SYSTEM SHALL <response>` —
one testable behavior per criterion:

> AC-1.1 WHEN an import completes, THE SYSTEM SHALL report the count of rows
> imported and rows rejected.

## Tasks in waves

Order `tasks.md` as waves: tasks within a wave are independent and can land in
parallel; each wave builds on the last. Every task names the gate that proves it.

## Public surface

`design.md` MUST declare the feature's **public surface**, designed in that order —
**structs before interfaces**. First the data: the structs, their fields, and the
invariants each field carries. Then the interfaces over them — signatures, protocols or
traits, wire formats, and config keys. Data shapes drive the operations, not the reverse.
This is the contract the naming and structure reviews grade against; a missing section is
a spec-stage gate failure. State each type once, as a code block where the language
allows; diagrams name the types and do not repeat their fields.

## Invariants

`design.md` MUST declare the feature's **invariants** — the properties that must always
hold (a gate that cannot be rationalized past, an append-only log, a value that defaults
once). State each so a reviewer can check the code against it; a missing section is a
spec-stage gate failure.

## Traceability

`design.md` SHOULD carry a table tracing each stated problem to its criteria, the
public-surface items they need, the tasks that build them, and the gate that proves each.
An item with no problem behind it is speculative scope; a problem no criterion covers is a
gap.

## Metrics

`design.md` SHOULD name the metrics that tell whether the feature works — the signals
to watch and how each is measured — or state **N/A** with a one-line reason. Define them
at spec time so success is testable, not asserted; N/A is an explicit answer, not silence.

## Diagrams

`design.md` SHOULD include a Mermaid **architecture** or component diagram — how the
structs and interfaces compose and where each stage runs — and a **class** diagram of
the designed types and their relationships; fields stay in the Public surface. A shell-only component with no typed structure uses
architecture plus data-flow instead of a class diagram. Diagrams are reviewed twice:
by `spec-review` at design time (accuracy and glossary vocabulary) and by `code-review`'s
docs-sync at build time (the diagram matches the shipped code; drift is a finding). Where
the feature has a core routine, the diagram locates each of its stages and the algorithm
in each context — not just the boxes.

## Review before approval

Use `spec-review` in fresh context on the changed spec files and apply its findings
before presenting `design.md` for approval.
