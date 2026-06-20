# AGENTS.md — order-shop

order-shop syncs confirmed Orders to the fulfillment partner behind a REST API.
Vocabulary lives in `knowledge/glossary.md`; per-feature detail in
`roadmap/specs/<feature>/`.

## Logging

One canonical **Wide event** per unit of work — a single structured log line with
all the fields for that operation. Production paths emit the Wide event and
nothing else; a raw `print`/`console.log` beside it is debt. A CLI surface such as
`print --help` is a user-facing command, not logging.

## Writing style

Strunk & White: omit needless words; use the active voice; make definite
assertions. Lead with the point; one idea per sentence.
