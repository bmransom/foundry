# Migration: OKF docs → knowledge (convention 1 → 2)

Moves a repo from the pre-OKF `docs/` layout to the OKF `knowledge/` + `roadmap/`
convention: `kind`→`type`, `docs.py`→`knowledge.py`, generated `index.md` + `log.md`.
The update skill runs this on a clean tree, on a branch, and verifies with the gate
(`../../SKILL.md` §3 Migrate). Steps split into **primitives** (deterministic — run
them exactly) and **judgment** (read the repo, then decide).

## Detect

Applicable when the repo carries any pre-OKF structural marker:

- a `.foundry-manifest.json` entry whose template is `docs` or `test-docs`,
- `scripts/docs.py`,
- `docs/docs-config.json`, or
- a top-level `docs/` directory.

A stray `kind:` field alone is *residue*, not a trigger — a correct migration leaves
none, so the detector never keys on it (idempotency).

## Preconditions

The update skill's preflight (`references/migrations/preflight.sh`) has already
refused a dirty tree and created `foundry/migrate-okf-knowledge` — so assume a clean
tree on that branch. New templates and seeds ship at
`<plugin>/templates/{verbatim,seeds}/`.

## Plan (dry-run)

Report, before writing: the file moves, the seeds to replace vs transform, and the
path-reference rewrites. Write nothing until reported.

## Transform — primitives (deterministic)

Path map, via `git mv` to preserve history:

| From | To |
|---|---|
| `docs/{glossary,validation,coe-template,README,index}.md` and any other `docs/*.md` concept | `knowledge/` |
| `docs/ROADMAP.md`, `docs/BACKLOG.md` | `roadmap/` |
| top-level `specs/` | `roadmap/specs/` |
| `docs/.vitepress/`, `docs/package.json`, `docs/tsconfig.json`, `docs/package-lock.json` | `knowledge/` |
| `crates/*/docs/` (Rust workspaces) | `crates/*/knowledge/` |

Then:

- `cp` the break's verbatim files byte-exact from `<plugin>/templates/verbatim/`:
  `scripts/{knowledge.py,test_knowledge.py,board.sh,worktree-retire.sh}`,
  `knowledge/{package.json,tsconfig.json,.vitepress/config.ts}`. Delete the old
  `scripts/docs.py`, `scripts/test_docs.py`, `docs/.vitepress/config.ts`. Keep scripts
  executable.
- Frontmatter: `kind:`→`type:` on every concept; drop the field from
  `roadmap/ROADMAP.md` and `roadmap/BACKLOG.md` (no longer concepts).
- Generate the listing: `python3 scripts/knowledge.py index`. Add `knowledge/log.md`
  (the seed) with a dated migration entry.
- Regenerate `.foundry-manifest.json` over the **complete** verbatim set (including the
  unaffected `.githooks/pre-push` and `scripts/install-hooks.sh`): each file's template
  name (from its `foundry-template:` marker — JSON files carry it in a `"//"` key),
  version, and `shasum -a 256`; set `conventionVersion: 2` and the plugin version.

## Transform — judgment (read the repo, then decide)

- **Config**: rewrite `docs/docs-config.json` → `knowledge/knowledge-config.json`.
  Rename `kinds`→`types`, `doc_globs`→`concept_globs`, `exclude_paths`→`reserved_files`
  (= `["knowledge/index.md","knowledge/log.md"]`); add `index_title` (the repo's site
  title, from the old `index.md` hero or `.vitepress/site.json`); carry over
  `lifecycles`, `required_fields`, `exclude_substrings`, `exclude_prefixes`, and
  `skill_ref_prefixes` (repath `docs/`→`knowledge/`, `specs/`→`roadmap/specs/`).
  `README.md` becomes a curated concept — drop it from any exclusion.
- **Path references**: rewrite `docs/`→`knowledge/` or `roadmap/` (whichever the target
  moved to) and bare `specs/`→`roadmap/specs/` in every file that carries them —
  `AGENTS.md`, `scripts/check-fast.sh` (`docs.py check`→`knowledge.py check`), the CI
  workflow (the docs-build job → knowledge), `.gitignore`, and
  `scripts/vocab-lint.sh` / `scripts/agent-env.sh` where the repo has them.
- **Rules**: add `.claude/rules/knowledge-conventions.md` (new seed); bring
  `spec-conventions.md` to the current seed (`paths:` → `roadmap/specs/**`, refs →
  `knowledge/glossary.md`).
- **Prose vocabulary**: `docs`→`concept(s)`, "kinds"→"types" where they name the
  knowledge base — not gate-enforced, so read meaning rather than blind-replace.

## Reconcile seeds

For each seed (glossary, validation, coe-template, README, ROADMAP, BACKLOG, the
rules, `site.json`) compare its `foundry-seed:` / `_foundry_seed` marker and content
to the shipped seed:

- **Pristine** (matches the prior seed) → replace with the current seed.
- **Customized** (diverged) → transform in place with the ops above, preserve the
  repo's content, and flag the divergence in the report. Never clobber.

## Self-verify

- `python3 scripts/knowledge.py check` exits 0.
- Residue scan: no `^kind:` frontmatter, no stale `docs/` path reference, no `docs.py`,
  no top-level `docs/` or `specs/`.
- Manifest sha256 matches disk for every entry; `conventionVersion: 2`.

Then hand back to the update skill, which runs the canonical gate (no-regression) and
its own independent residue scan — the migrator never grades itself.
