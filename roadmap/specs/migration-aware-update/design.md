> **Status:** In progress (2026-06-14) — tracked on the [board](../../ROADMAP.md).

# Design — migration-aware update

## Architecture overview

The `update` skill gains a **migration pre-flight** ahead of its existing
verbatim/seed refresh. Today update is five phases (read state → compare verbatim →
compare seeds → report → verify). This feature inserts detection-and-migration
between reading state and comparing: update places the repo on a *convention
version*, builds the ordered chain of migrations from the repo's convention to the
plugin's, runs them, then falls through to the unchanged refresh — which now finds a
correctly-named, current manifest and reconciles any drift unrelated to the break.

Migrations are **agent-orchestrated playbooks in a registry**, not codemod binaries.
The agent runs each playbook; the deterministic, must-not-vary steps (byte-exact
recopy, `knowledge.py index`, manifest regeneration) go through fixed primitives;
the consumer's gate — sharing no code with the migrator — is the acceptance test.
A migration is keyed to the convention version it *produces*; the registry is
ordered by that key. The OKF `docs/`→`knowledge/`+`roadmap/` break is convention 2
(pre-OKF repos are convention 1) and ships as the registry's first entry.

## Components

| Component | Location | New / modified | Purpose |
|---|---|---|---|
| Migration pre-flight | `plugins/foundry/skills/update/SKILL.md` | modified | Detect convention, build the chain, run migrations before the standard refresh |
| Migration registry | `plugins/foundry/skills/update/references/migrations/README.md` | new | Ordered table keyed by convention version: `id`, from→to, detector, playbook link |
| OKF migration playbook | `plugins/foundry/skills/update/references/migrations/okf-knowledge.md` | new | The proven docs→knowledge transform: detect, plan, transform, reconcile seeds, manifest, verify |
| `conventionVersion` field | manifest schema — `bootstrap` SKILL.md §3 Copy, `update` SKILL.md §1 | modified | The monotonic convention marker bootstrap writes and update reads |
| Migration eval | `evals/harness/migration-eval.sh` | new | Headless run + harness-owned invariants (structure, residue, gate, manifest, chaining) |
| Migration fixtures | `evals/fixtures/migration-*/` | new | The fixture matrix (Testing): stack, customized, scale, legacy, partial, dirty, red-gate — each a pre-OKF repo |
| Fixture-builder | `evals/harness/build-migration-fixtures.sh` | new | Freezes old-convention snapshots from the stack fixtures so they track the real old shape |

## Data models

**Manifest, with the new field** (top-level, beside `pluginVersion` / `files`):

```json
{ "pluginVersion": "0.2.0", "conventionVersion": 2, "files": { … } }
```

`conventionVersion` is an integer bumped *only* by a convention break, independent
of plugin semver — the version reset (consumers stamped `"1.0.0"`, plugin now
`0.1.0`) makes semver useless for ordering, so convention version carries it. Absent
→ the repo predates this field; place it by detection (AC-4.2).

**Registry entry** (a row in `references/migrations/README.md`):

| Field | Meaning |
|---|---|
| `convention` | The version this migration produces (its sort key); applied when `repo < convention ≤ plugin` |
| `id` | Stable slug, e.g. `okf-knowledge` |
| `detector` | The structural test that fires on the *prior* convention (AC-1.1 markers) |
| `playbook` | The `references/migrations/<id>.md` to execute |

**Playbook structure** (`okf-knowledge.md`) — the captured, proven sequence:

1. **Detect** — markers: a manifest `docs`/`test-docs` entry, `scripts/docs.py`,
   `docs/docs-config.json`, or any `kind:` concept. None → not applicable (no-op).
2. **Preconditions** — clean working tree, else refuse (AC-1.3).
3. **Plan** — emit the move/transform/seed report before writing (AC-1.4).
4. **Transform** — split into *primitives* (deterministic) and *judgment* (agent):

| Primitive (fixed, must not vary) | Judgment (agent reads meaning) |
|---|---|
| `git mv` by the path map: `docs/{concepts}`→`knowledge/`, `docs/{ROADMAP,BACKLOG}`→`roadmap/`, `specs/`→`roadmap/specs/`, vitepress→`knowledge/` | classify each seed pristine vs customized (marker+hash) → replace vs transform-and-flag (AC-2.6) |
| `cp` the break's verbatim files byte-exact — `scripts/{knowledge.py,test_knowledge.py,board.sh,worktree-retire.sh}`, `knowledge/{package.json,tsconfig.json,.vitepress/config.ts}` | rewrite path refs to the *right* target (`docs/`→`knowledge/` vs `roadmap/`) (AC-2.5) |
| `kind:`→`type:` on the known concept set; drop on `ROADMAP`/`BACKLOG` (AC-2.2) | carry over repo-specific config: polarity, exclusions, `index_title` from old hero/`site.json` (AC-2.3) |
| `knowledge.py index`; append `log.md` entry (AC-2.7) | prose vocab (`docs`→`concept`, "kinds"→"types") — not gate-enforced |
| manifest regen over the *complete* verbatim set (incl. unaffected `pre-push`, `install-hooks.sh`): rehash all, remap names/paths, stamp `conventionVersion` (AC-2.4) | adapt to drift the fixture lacks (extra concepts, crate docs, a hand-edited gate) |

5. **Verify (self-check)** — `knowledge.py check` and a residue scan, then hand back
   to update. The eval re-verifies independently with its own scan (§Testing).

## Data flow

Participants: **caller**, **update skill (agent)**, **repo/filesystem**, **gate**.

1. Caller runs `/foundry:update`.
2. Agent reads `.foundry-manifest.json` → `pluginVersion`, `conventionVersion`,
   `files`. Absent → Legacy (detect from disk).
3. Agent determines repo convention: the stamped `conventionVersion`, else the
   earliest convention whose detector fires (AC-4.2). The plugin's convention is the
   registry head — the highest `convention` across registry rows, the single source
   of truth (one number to bump per break).
4. Agent builds the chain: every registry entry with `repo < convention ≤ plugin`,
   ascending (AC-4.1). Empty → skip to step 8 (standard update unchanged, AC-1.2).
5. **Gate: clean tree** (AC-1.3); a **dry-run report** of the full chain that writes
   nothing (AC-1.4); then **branch** to `foundry/migrate-<id>` so the working branch
   is untouched (AC-1.5). Dirty or unplaceable → stop and instruct; never guess.
   Capture the canonical gate's pre-migration baseline here (AC-3.1).
6. For each migration in order (AC-4.3): run primitives, then judgment; regenerate
   `index.md`/`log.md`; re-run the structure + frontmatter checks. A step that fails
   stops the chain, preserves prior steps, names the culprit (AC-4.5).
7. After the last migration, stamp the plugin's `conventionVersion` (AC-4.6).
8. Standard update phases run (compare verbatim → seeds → report → apply) over the
   now-current convention, catching any refresh unrelated to the break.
9. **Verify** (AC-3.1): migration-specific checks green (`knowledge.py check`,
   structure, completeness — zero residue, AC-3.2); the canonical gate must not
   regress against the step-5 baseline (a pre-existing red gate is reported, not
   blamed); ask before committing or merging the branch.

## Error handling

| Failure mode | Handling |
|---|---|
| Dirty working tree | Refuse; instruct the caller to commit a baseline (AC-1.3). No partial writes. |
| Convention unplaceable (ambiguous/missing markers) | Stop, report, ask — never guess (mirrors Legacy mode). |
| Customized seed | Transform in place, flag the divergence in the report; never clobber (AC-2.6). |
| Mid-chain step fails its post-step check | Stop at that step; earlier migrations stay applied and committable; name the failed migration (AC-4.5). |
| Canonical gate *regressed* (new failures vs. baseline) | Report the diff; do not commit; abandon the branch (AC-1.5, AC-3.1). |
| Canonical gate red *before* migration | Proceed; migration-specific checks still gate correctness; report the pre-existing failure, never claim a clean PASS (AC-3.1). |
| Residue after a "success" (a `kind:`, a `docs/` ref, `docs.py`, manifest sha mismatch) | Completeness failure, not a PASS (AC-3.2). |
| Partially hand-migrated repo | Idempotent detectors fire only on residue and complete it (AC-4.4). |

## Testing strategy

**Independent oracle.** Grading is harness-owned — structural assertions, a
completeness grep, manifest sha recomputation, and the repo's own gate. None shares
code with the migrator; the migrator's own claims never grade it (global rule:
independent verification).

**Fixture matrix.** One happy-path fixture cannot earn confidence for arbitrary
consumer repos. The eval runs the same harness-owned grade across a matrix covering
the real risk surface:

| Fixture | Risk it covers |
|---|---|
| `migration-okf/` (TS) | Baseline happy path |
| `migration-rust/` (workspace) | Stack + `crates/*/docs/`→`crates/*/knowledge/` completeness |
| `migration-python/` (service) | Stack: ruff/pytest gate, service shape |
| `migration-customized/` | Edited glossary, ROADMAP, rule — transform-and-flag, never clobber (AC-2.6) |
| `migration-scale/` | Dozens of concepts, multiple specs, extra rules — completeness at scale |
| `migration-legacy/` | No manifest — detection by structure (AC-4.2) |
| `migration-partial/` | Half-hand-migrated — idempotent convergence (AC-4.4) |
| `migration-dirty/` | Dirty tree — refusal, zero writes (AC-1.3) |
| `migration-redgate/` | Gate red before migration — no-regression, not blamed (AC-3.1) |

Stack fixtures derive from `evals/fixtures/{rust-cli,ts-monorepo,python-service}`
frozen on the *old* convention by a fixture-builder. Each fixture carries a
discrimination variant — a seeded incomplete migration the harness scan must fail.

**`migration-eval.sh` (Layer 2)** — the `update-eval.sh` pattern: for each fixture,
copy it to scratch, `git init` a baseline, run `/foundry:update` headless
(`claude -p --plugin-dir`), then grade invariants per AC:

- *Structure* — `knowledge/` and `roadmap/specs/` present; no `docs/`, no `specs/`,
  no `docs.py` (AC-2.1).
- *Frontmatter* — every concept `type:`, none `kind:` (AC-2.2, AC-3.2).
- *Tooling/manifest* — verbatim files byte-identical to current templates; manifest
  sha matches disk; `conventionVersion == 2`; `pluginVersion` bumped (AC-2.4, AC-4.6).
- *Knowledge* — `knowledge.py check` exits 0; `index.md` fresh; `log.md` has a dated
  entry (AC-2.7).
- *Gate + history* — canonical gate green (AC-3.1); `git` shows renames, not
  delete-plus-create (AC-2.1); a migration commit exists.

**Discrimination** (the eval must catch a bad migration, not just confirm a good
one) — graded by a **harness-owned** residue scan, never the migrator's own checks.
The migrator certifying itself is the circular verification AGENTS.md forbids; and
`knowledge.py check` alone misses a stale `docs/` ref or a roadmap `kind:`, since it
lints only `knowledge/**`:
- Seed an incomplete migration (one un-flipped `kind:`, one stale `docs/` ref) into a
  scratch tree; the harness's own scan over the migrated tree MUST report failure —
  proving the eval, not the migrator, catches incompleteness.
- *Chaining* (AC-4.3): doctor a plugin copy (as `update-eval` builds v-next) with a
  synthetic convention-3 migration and `conventionVersion: 3`; run update on the
  convention-1 fixture; the harness asserts it arrives at convention 3 with both
  migrations applied in order — proving the loop sequences, not fires once.

**Unit.** Deterministic primitives reused from existing, already-tested tooling
(`cp`, `knowledge.py`); no new parser to unit-test. Any extracted manifest-regen
helper gets a unit test before it ships.

## Performance

Negligible — a one-time, human-initiated operation. The only real cost is the gate;
the full canonical gate runs once at the end (AC-3.1), with lightweight structure +
frontmatter checks between chain steps (AC-4.3), not the whole heavy gate per step.

## Migration / backward-compatibility

- **Legacy unstamped repos** (every repo bootstrapped before this feature, including
  real consumers) carry no `conventionVersion`; detection places them (AC-4.2). This
  is the common path today.
- **bootstrap must start stamping** `conventionVersion` so future updates are
  version-gated — a small `bootstrap/SKILL.md` §3 + manifest-doc change (a task
  below). New bootstraps stamp convention 2.
- **No downgrade.** Rollback is `git revert` of the migration commit (out of scope:
  inverse migrations).

## Acceptance-criteria traceability

| AC | Design coverage |
|---|---|
| 1.1 detect | Data flow 2–3; registry detectors; playbook §Detect |
| 1.2 skip when none | Data flow 4 (empty chain) |
| 1.3 dirty refuse | Data flow 5; Error handling |
| 1.4 dry-run report | Data flow 5; playbook §Plan |
| 1.5 branch isolation | Data flow 5; Error handling; Story 3 |
| 2.1–2.7 OKF transform | OKF playbook §Transform table; Data flow 6 |
| 3.1 verify (no-regression) | Data flow 5 (baseline) + 9 |
| 3.2 completeness | Data flow 9; Error handling; Testing (discrimination) |
| 4.1 ordered registry | Data model (registry entry); Data flow 4 |
| 4.2 stamped-or-detected | Data model (`conventionVersion`); Data flow 3 |
| 4.3 sequential, re-check | Data flow 6; Testing (chaining) |
| 4.4 idempotent | Error handling (partial repo) |
| 4.5 stop on failure | Data flow 6; Error handling |
| 4.6 stamp on completion | Data flow 7 |
