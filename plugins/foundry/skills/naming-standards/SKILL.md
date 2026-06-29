---
name: naming-standards
description: Use when choosing, reviewing, or changing names for features, concepts, glossary terms, APIs, modules, files, directories, fields, flags, metrics, tests, configs, commands, public types, or user-facing vocabulary.
---

# Naming Standards

Names are contracts. Prefer names that make the domain model, responsibility, and change intent obvious without extra comments.

## Order Of Authority

1. Follow repo conventions and the existing glossary first.
2. Prefer the domain's established terms over invented names.
3. Follow language/framework naming style when the repo has no stronger rule.
4. If no prior term fits, coin one deliberately and record the provenance or tradeoff.

## Review Checklist

- Use readable, descriptive names; favor clarity over brevity.
- Avoid abbreviations, contractions, and acronyms unless they are established in the domain.
- Avoid generic buckets: `data`, `info`, `manager`, `helper`, `utils`, `misc`, `common`.
- Name types and modules by responsibility; name functions by action or returned concept.
- Name booleans as predicates: `isReady`, `hasAccess`, `shouldRetry`.
- Name metrics with unit and scope: `request_duration_ms`, `tokens_per_second`.
- Name files/directories according to repo convention; otherwise prefer lowercase hyphen-case for prose/tooling files and language-standard names for source files.
- Keep old and new API versions discoverable near each other when replacing an API.

## Spec Loop

During spec review, inspect every new canonical term, public API, config knob, metric,
directory, and persisted field. Search comparable tools or standards when the name shapes
user understanding. Update `knowledge/glossary.md` for terms the repo should keep using.

## Examples

| Weak | Stronger | Reason |
|---|---|---|
| `ThingManager` | `SubscriptionRegistry` | Names owned concept and responsibility. |
| `processData()` | `normalizeInvoiceLines()` | Names the action and object. |
| `fast_mode` | `skip_remote_validation` | Names behavior, not vague intent. |
| `duration` | `build_duration_ms` | Includes scope and unit. |

## Traps

- Do not choose names only because they are short.
- Do not leak implementation types into public names unless the type is the domain.
- Do not rename widely-used concepts without a migration plan.
- Do not bury a contested term in code; settle it in the spec or glossary.
