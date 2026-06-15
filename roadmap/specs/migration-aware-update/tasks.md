> **Status:** In progress (2026-06-14) — tracked on the [board](../../ROADMAP.md).

# Tasks — migration-aware update

Waves run top to bottom; tasks within a wave have no inter-dependencies. The build
order is tiered (the design's testing decision): the safety net and the three
"scary" fixtures land first; stack/scale/customized coverage accretes COE-style.

## Wave 1: Convention-version plumbing (no dependencies)

- [ ] **T1** Add `conventionVersion` to the manifest: bootstrap writes it (current
  convention = 2) and the manifest shape documents it —
  `plugins/foundry/skills/bootstrap/SKILL.md` (§3 Copy). → AC-4.2, AC-4.6
- [ ] **T2** Migration registry: an ordered table keyed by convention version, the
  registry-head rule (the plugin's convention = the max row), and how update
  consumes it — `plugins/foundry/skills/update/references/migrations/README.md`.
  → AC-4.1

## Wave 2: OKF migration + orchestration (depends: Wave 1)

- [ ] **T3** OKF migration playbook — detect, preconditions, dry-run plan, transform
  (the primitives/judgment split, including `crates/*/docs/`→`crates/*/knowledge/`),
  seed reconcile, manifest regen, self-verify —
  `plugins/foundry/skills/update/references/migrations/okf-knowledge.md`.
  → AC-2.1–2.7
- [ ] **T4** Update-skill migration pre-flight — read `conventionVersion`; detect and
  place the repo; build and dry-run-report the chain; clean-tree gate; branch to
  `foundry/migrate-<id>`; run the chain with a re-check between steps; no-regression
  verify against a pre-migration baseline; stamp the convention; hand to the standard
  refresh — `plugins/foundry/skills/update/SKILL.md`.
  → AC-1.1–1.5, AC-3.1, AC-3.2, AC-4.1–4.6

## Wave 3: Eval infrastructure (depends: Wave 2)

- [ ] **T5** Fixture-builder — freeze old-convention (`docs/`, `docs.py`, `kind:`,
  `docs`/`test-docs` manifest, no `conventionVersion`) snapshots from the existing
  stack fixtures, and assemble the synthetic ones —
  `evals/harness/build-migration-fixtures.sh`.
- [ ] **T6** Migration eval harness — the `update-eval.sh` pattern: per fixture, copy
  to scratch, `git init` baseline, run `/foundry:update` headless, then grade
  harness-owned invariants (structure, **residue scan**, manifest sha, gate
  no-regression, branch present, history-preserving renames) —
  `evals/harness/migration-eval.sh`. → AC-3.2 (independent oracle)

## Wave 4: Tier-1 fixtures + run (depends: Wave 3)

- [ ] **T7** Tier-1 fixtures, each with a discrimination variant (a seeded
  incomplete migration the residue scan must fail): `migration-okf` (TS baseline),
  `migration-legacy` (no manifest), `migration-dirty`, `migration-redgate` —
  `evals/fixtures/migration-*/`. → AC-1.3, AC-3.1, AC-4.2
- [ ] **T8** Run `migration-eval.sh` across tier-1, plus: the **chaining** case
  (doctor a plugin copy with a synthetic convention-3 migration → assert a
  convention-1 fixture arrives at 3, in order), an **idempotency** re-run (migrate an
  already-migrated tree → no change), and a **forced mid-chain failure** (assert
  stop + prior steps preserved). Record to `evals/results/`.
  → AC-1.1, AC-1.2, AC-4.3, AC-4.4, AC-4.5, AC-4.6

## Wave 5: Verification

- [ ] Run `scripts/check-fast.sh` — foundry self-host gate (byte-identity, knowledge
  check, script tests). Must PASS.
- [ ] Confirm `migration-eval.sh` tier-1 + chaining + idempotency + forced-failure
  all green; paste results.
- [ ] Regression smoke: `update-eval.sh` and a `bootstrap` smoke still green after
  the bootstrap/update skill changes (the `conventionVersion` add is additive).
- [ ] Manually verify each acceptance criterion against the implementation.
- [ ] Board: set the `roadmap/ROADMAP.md` card to Validating with the recorded gate +
  eval results.
- [ ] Capture the deferred tier-2 fixtures as `roadmap/BACKLOG.md` items.

## Deferred — Tier-2 coverage (accrete COE-style)

Per the build-order decision: the safety net makes an un-covered case fail loudly and
abandonable, not catastrophic — so breadth accretes as real repos surface it. Tracked
in `roadmap/BACKLOG.md`, promoted to the board on demand or on a COE:

- `migration-rust` (+ `crates/*/docs/`) and `migration-python` — stack breadth.
- `migration-customized` — customized-seed transform-and-flag (AC-2.6) at depth.
- `migration-scale` — completeness across dozens of concepts + multiple specs.
- `migration-partial` — idempotent convergence on a half-hand-migrated repo (AC-4.4
  beyond the simple re-run).

## Acceptance-criteria traceability

| AC | Built by | Tested by |
|---|---|---|
| 1.1 detect | T4 | T8, T7 (legacy) |
| 1.2 skip when none | T4 | T8 |
| 1.3 dirty refuse | T4 | T7 (dirty) |
| 1.4 dry-run report | T4 | T8 |
| 1.5 branch isolation | T4 | T8 (branch present) |
| 2.1–2.7 OKF transform | T3 | T7/T8 (okf) |
| 3.1 no-regression verify | T4 | T7 (redgate) |
| 3.2 completeness | T4 (self), T6 (harness scan) | T7 discrimination variants |
| 4.1 ordered registry | T2 | T8 (chaining) |
| 4.2 stamped/detected | T1, T4 | T7 (legacy) |
| 4.3 sequencing | T4 | T8 (chaining) |
| 4.4 idempotent | T3, T4 | T8 (re-run); T7 partial deferred |
| 4.5 stop on failure | T4 | T8 (forced failure) |
| 4.6 stamp on completion | T1, T4 | T7/T8 (manifest `conventionVersion`) |
