# Knowledge stage rubric

Place the change in the knowledge base and keep the base coherent. The base is a Google
**Open Knowledge Format** bundle — one concept per file, `type` frontmatter, a generated
`index.md`, an append-only `log.md`, links as a graph. The reading is easy; the
bookkeeping is the work.

## Intent

Every durable fact the change created lands in its right home, findable by the next
reader, with nothing left stale, orphaned, or contradictory.

## Pick the home first

| The change is… | Home |
|---|---|
| a **canonical name** the repo should keep using | a row in `knowledge/glossary.md`, with provenance |
| a durable **explanation, contract, how-to, or decision** | a concept file under `knowledge/`, with an OKF type |
| a standing **rule, boundary, or convention** | `AGENTS.md` (or `rules/`) |
| the **record** that something changed | a `knowledge/log.md` entry, appended newest-first |

One fact often touches several homes at once.

## The four OKF types

- **reference** — evergreen lookup or contract.
- **architecture** — how the system is built, and why.
- **guide** — a task-oriented how-to.
- **decision** — a dated record: a correction of error, an experiment, an investigation.

## Invariants

- A canonical name carries its prior-art provenance; a claim is anchored to the source it
  describes.
- A re-touch **appends** — a `log.md` entry or a new History line — never a silent
  rewrite that loses the *why*.
- No **orphan** (a concept nothing links to), no **stale** claim a newer source
  superseded, no **missing page** (a heavily-referenced idea with no file), no
  **contradiction** (two files disagreeing about the same concept).
- Progressive disclosure holds: the `index` is regenerated, each concept has a tight
  one-line `description` and clear headings, and a superseded claim is marked
  `lifecycle: superseded` rather than deleted.

## Output contract

The knowledge gate is command-shaped: the driver runs the mechanical knowledge check and
regenerates the index; it passes when the check is clean and the index is current. This
rubric states what good placement holds; there is no marker to emit.
