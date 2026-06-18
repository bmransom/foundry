---
name: modular-structure
description: Use when designing, reviewing, or refactoring directory layout, module boundaries, package structure, layering, public APIs, dependency direction, ownership boundaries, cohesion, coupling, or where new code should live.
---

# Modular Structure

A clean structure makes ownership and dependency direction obvious. Put code where
future maintainers will look first, and keep each module's reason to change narrow.

## Principles

- Follow the repo's existing layout before inventing a new one.
- Group by domain capability when features evolve together; group by technical layer only when the repo already does.
- Keep high-cohesion code together and low-coupling boundaries explicit.
- Separate public entrypoints from internal helpers.
- Keep adapters at the edge: CLI, HTTP, database, filesystem, vendor clients, model/tool calls.
- Avoid dumping grounds: `utils`, `common`, `shared`, `helpers`, `lib` need a sharper name or a narrower API.
- Keep tests near the code or in the repo's conventional test tree; mirror names when it helps navigation.

## Directory Review

During spec and plan review, answer:

- Which existing module owns this behavior?
- What new directory, if any, represents a stable domain concept?
- What depends on what? Does dependency direction match the architecture?
- Which files are public API, and which are internal?
- Where will tests, fixtures, generated output, and performance artifacts live?
- What old path becomes obsolete, and how will it be migrated or deleted?

## Common Shapes

| Need | Shape |
|---|---|
| Domain logic | `domain/<capability>/` or the repo's equivalent feature/module path. |
| External system boundary | `adapters/<system>/`, `integrations/<system>/`, or existing edge layer. |
| App entrypoint | `cmd/`, `api/`, `routes/`, `cli/`, or framework convention. |
| Shared contract | A named package such as `events`, `schema`, `protocol`, or `contracts`. |
| Performance work | `performance/<topic-or-date>/` unless the repo already has a benchmark convention. |

## Traps

- Do not create a new top-level directory for one file unless it names a stable concept.
- Do not split tightly-coupled code across directories to appear modular.
- Do not centralize unrelated helpers under a vague shared module.
- Do not hide generated files or bulky run artifacts in source directories.
