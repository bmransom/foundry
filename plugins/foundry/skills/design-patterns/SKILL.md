---
name: design-patterns
description: Use when choosing, reviewing, or refactoring object, module, or service interactions; extension points; algorithm selection; adapters; eventing; construction; dependency boundaries; or when Strategy, Observer, Adapter, Factory, Builder, Facade, Decorator, Command, State, or similar patterns may fit.
---

# Design Patterns

Use patterns as names for recurring design forces, not decoration. State the
problem, the candidate pattern, the simpler alternative, and why the pattern earns
its complexity in this repo.

## Decision Rules

- Prefer the repo's existing architecture and idioms before introducing a pattern.
- Prefer composition over inheritance unless the relationship is truly "is-a".
- Keep the public interface small; hide construction, IO, and vendor details at boundaries.
- Choose the lightest pattern that removes real duplication, isolates volatility,
  or makes an extension point explicit.
- Reject pattern cosplay: if a function, map, or small module is clearer, use it.

## Pattern Catalog

| Pattern | Use When | Example |
|---|---|---|
| Strategy | Several interchangeable algorithms or policies share one contract. | `RetryPolicy`, `RankingStrategy`, or `PricingStrategy` selected by config. |
| Adapter | Existing, legacy, vendor, or external interfaces do not match the local contract. | Wrap a library client so app code sees `SearchIndex` instead of vendor calls. |
| Observer | Publishers emit events to dynamic subscribers without depending on concrete receivers. | Domain event subscribers update logs, metrics, cache, or notifications. |
| Factory Method | Creation varies by subtype or environment and callers should not know concrete classes. | Build the right storage client from config. |
| Builder | A valid object needs staged construction or many optional fields. | Assemble a query, report, or request with validation at `build()`. |
| Facade | A subsystem is noisy and callers need one stable entrypoint. | `BillingService` hides gateway, tax, and invoice collaborators. |
| Decorator | Add behavior around the same interface without changing the wrapped object. | Add caching, tracing, or retries around a client. |
| Command | Operations need queueing, retry, logging, undo, or remote execution. | Persist `ImportJob` commands for workers. |
| State | Behavior changes by lifecycle state and conditionals are spreading. | `Draft`, `Published`, and `Archived` handle allowed transitions. |

## Spec Loop

During design review, ask:

- What varies, and how often will it vary?
- What boundary protects the rest of the code from that variation?
- What simpler design would fail under the expected change?
- What tests prove the pattern's contract?

Record the chosen pattern and rejected simpler alternative in the design only when
the choice materially shapes implementation.

## Traps

- Do not introduce a pattern because the name sounds senior.
- Do not make every concept an interface before there is variation.
- Do not use Singleton to hide global mutable state.
- Do not let Adapter become a dumping ground for business logic.
