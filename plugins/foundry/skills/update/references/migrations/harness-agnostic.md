# Migration: harness-agnostic (convention 2 → 3)

Brings a repo from the Claude-only convention-2 layout to the harness-agnostic
convention-3 layout: rules off `.claude/`, the manifest under `.foundry/`, and a
recorded harness set. The update skill runs this on a clean tree, on a branch, and
verifies with the gate (`../../SKILL.md` §3 Migrate). Steps split into **primitives**
(deterministic — run them exactly) and **judgment** (read the repo, then decide).

## Detect

Applicable when the repo carries a pre-harness-agnostic structural marker:

- a top-level `.foundry-manifest.json` (the manifest not yet under `.foundry/`), or
- a `.claude/rules/` directory.

A correct migration removes both, so the detector never re-triggers (idempotency).

## Preconditions

The update skill's preflight (`references/migrations/preflight.sh`) has already refused
a dirty tree and created `foundry/migrate-harness-agnostic` — so assume a clean tree on
that branch. The current rules seed ships at `<plugin>/templates/seeds/rules/`.

## Plan (dry-run)

Report, before writing: the two moves, the path-reference rewrites, and the harness set
to record. Write nothing until reported.

## Transform — primitives (deterministic)

Moves, via `git mv` to preserve history:

| From | To |
|---|---|
| `.claude/rules/` (the rules seeds) | `rules/` |
| `.foundry-manifest.json` | `.foundry/manifest.json` |

Then:

- Remove the emptied `.claude/` directory if nothing else remains in it.
- Stamp the manifest: add `"conventionVersion": 3` and the inferred `harnesses` array
  (below) beside the existing `pluginVersion` and `files`.

## Transform — judgment (read the repo, then decide)

- **Harness set**: infer the repo's current harnesses from what it carries — a
  `CLAUDE.md` → `claude-code`; a `.codex-plugin/` or `.agents/skills/` → `codex`. A repo
  bootstrapped before this feature is Claude-only → `["claude-code"]`. Record the
  inferred set; the caller may add a harness afterward (update §Add a harness).
- **Path references**: rewrite `.claude/rules/` → `rules/` in every file that names the
  path — among them `AGENTS.md`, `scripts/check-fast.sh`, the CI workflow, and
  `.gitignore` where present. Read each file; a `.claude/` in prose about Claude Code is
  not a path to rewrite.

## Reconcile seeds

The rules are seeds. Compare each rule's `foundry-seed:` marker and content to the
shipped seed under `<plugin>/templates/seeds/rules/`:

- **Pristine** (matches the prior seed) → replace with the current seed at the new path.
- **Customized** (diverged) → move it, preserve the repo's content, and flag the
  divergence in the report. Never clobber.

## Self-verify

- No `.claude/rules/` directory; no top-level `.foundry-manifest.json`.
- `.foundry/manifest.json` carries `conventionVersion: 3` and a `harnesses` array; its
  sha256 entries match disk.
- `python3 scripts/knowledge.py check` exits 0; no stale `.claude/rules/` path reference
  remains.

Then hand back to the update skill, which runs the canonical gate (no-regression) and
its own independent residue scan — the migrator never grades itself.
