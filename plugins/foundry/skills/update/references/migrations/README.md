# Migration registry

`/foundry:update` consults this registry to cross *convention breaks* — releases
that rename templates, move directories, or change frontmatter. Each migration is a
playbook the update skill runs; the consumer's gate verifies the result.

## How update uses it

1. Read the repo's convention version: `.foundry-manifest.json` `conventionVersion`,
   else infer it by the earliest detector that fires (a repo bootstrapped before the
   field existed).
2. The plugin's convention version is the **registry head** — the highest
   `Convention` row below. This is the single source of truth; bump it here when a
   break ships.
3. Apply every migration with `repo < Convention ≤ head`, in ascending order. Each
   runs on the previous one's output (see the update skill's migration phase).
4. After the chain, stamp `conventionVersion = head` in the manifest, so the next
   update is version-gated and skips detection.

A migration's **detector** keys only on structural signals a correct migration
removes, so an already-migrated repo never re-triggers (idempotent). Frontmatter
residue such as a stray `kind:` is a completeness failure, never a trigger.

## Migrations

| Convention | id | From → To | Detector | Playbook |
|---|---|---|---|---|
| 2 | `okf-knowledge` | `docs/` concepts and a top-level `specs/` → `knowledge/` + `roadmap/`; `kind`→`type` | a manifest `docs`/`test-docs` entry, `scripts/docs.py`, `docs/docs-config.json`, or a top-level `docs/` directory | [okf-knowledge.md](okf-knowledge.md) |

Convention 1 is the pre-OKF `docs/` layout — no row, because nothing migrates *to* it.
