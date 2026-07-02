# Migration registry

`foundry update` consults this registry to cross *convention breaks* — releases
that rename templates, move directories, or change frontmatter. Each migration is a
code module beside this file (`m<NNN>_<name>.py`) with `applies(repo)` and
`apply(repo)`; the consumer's gate verifies the result.

## How update uses it

1. Read the repo's convention version: `.foundry/manifest.json` `conventionVersion`
   (legacy: a top-level `.foundry-manifest.json`), else infer it by the earliest
   detector that fires (a repo bootstrapped before the field existed).
2. The plugin's convention version is the **registry head** — the highest
   `Convention` row below. This is the single source of truth; bump it here when a
   break ships.
3. Apply every migration with `repo < Convention ≤ head`, in ascending order. Each
   runs on the previous one's output.
4. After the chain, stamp `conventionVersion = head` in the manifest, so the next
   update is version-gated and skips detection.

A migration's `applies(repo)` keys only on structural signals a correct migration
removes, so an already-migrated repo never re-triggers (idempotent). Frontmatter
residue such as a stray `kind:` is a completeness failure, never a trigger.

## Migrations

| Convention | id | From → To | Detector | Module |
|---|---|---|---|---|
| 2 | `okf-knowledge` | `docs/` concepts and a top-level `specs/` → `knowledge/` + `roadmap/`; `kind`→`type` | a manifest `docs`/`test-docs` entry, `scripts/docs.py`, `docs/docs-config.json`, or a top-level `docs/` directory | `m002_okf_knowledge.py` |
| 3 | `harness-agnostic` | `.claude/rules/` → `rules/`; `.foundry-manifest.json` → `.foundry/manifest.json`; record the harness set | a top-level `.foundry-manifest.json` (manifest not yet under `.foundry/`) or a `.claude/rules/` directory | `m003_harness_agnostic.py` |
| 4 | `card-ids` | board gains a required slug-safe `Id` column (on claimable cards), enforced by `check-board.py` | a `roadmap/ROADMAP.md` card-table header with no `Id` column, or a manifest `conventionVersion < 4` | `m004_card_ids.py` |
| 5 | `pinned-run` | vendored gate scripts retire for the pinned `uvx … foundry gate` command: rewrite `.githooks/pre-push` + CI, delete `check-board.py`/`prose-lint.py`, write `.foundry/config.toml` | a manifest `conventionVersion == 4` with a vendored gate script or a check-fast pre-push | `m005_pinned_run.py` |

Convention 1 is the pre-OKF `docs/` layout — no row, because nothing migrates *to* it.

**Self-host divergence.** Consumer repos get m005's pinned `uvx --from "git+<repo>@<pin>"
foundry gate` in `.githooks/pre-push` and CI. Foundry's own repo diverges: its pre-push
and CI run the LOCAL tree (`uv run … foundry gate`), so the repo gates its current code
with its current tools — a pinned fetch would gate a stale tag. `check-gate-tools.sh`
asserts registry head == this repo's manifest convention; both moved to 5 together with
this self-host application.
