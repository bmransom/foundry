---
title: Foundry Roadmap
description: The tracked kanban board — the single source of truth for cross-spec status.
---

# Foundry Roadmap

This board is the single source of truth for cross-spec status, sequencing, and
ownership. When a per-feature spec and this board disagree, the board wins; every spec
carries a status header that points here.

## Board conventions

- A **card** is one table row: `Id | Work | Status | Spec | Depends on`. The `Id` is a
  unique, slug-safe (`^[a-z0-9][a-z0-9-]*$`) handle — required on claimable cards (Ready /
  In progress / Validating), enforced by `scripts/check-board.py` in the gate. Claim a card
  by adding `(@<owner>)` to its Work cell.
- An **In progress** card names where its work lives: the branch, and the absolute
  worktree path when the work sits in a separate or out-of-repo worktree — so a harness
  picking it up finds existing work instead of guessing.
- Status flow: `Backlog → Ready → In progress → Validating → Done` (+ `Planned`,
  `Blocked` as a flag, `Superseded` terminal).
- **`Done` requires a recorded gate PASS** once the gate exists — the gate is the
  evaluator, not the author's assertion.

## Standing rules

**Naming.** `knowledge/glossary.md` is the vocabulary contract. In particular: a *template*
is a file foundry copies or renders into a consumer repo; a *fixture* is an eval
target repo; a *seeded defect* is a deliberate fault a generated gate must catch.

**Mechanisms, not content.** No template carries any repo's entity
model, forbidden terms, standing rules, or gate commands.

## Status Dashboard

### Epic 0 — Foundry v1

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | foundry-core spec: requirements + design | Done — spec approved 2026-06-10 | `roadmap/specs/foundry-core/` | — |
|  | Plugin skeleton: marketplace.json, plugin.json, repo self-host scaffold, `check-fast.sh` + self-host byte-identity gate | Done — gate recorded 2026-06-10: check-fast: PASS | `roadmap/specs/foundry-core/` | spec approval |
|  | Template extraction from the reference repo (@main): knowledge.py (parameterized), board.sh, vitepress scaffold, ROADMAP/glossary/spec-conventions/COE templates, githooks, worktree-retire | Done — gate recorded 2026-06-10: check-fast: PASS | `roadmap/specs/foundry-core/` | plugin skeleton |
|  | `code` lifecycle skill, generalized (reads repo AGENTS.md for commands/paths) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | template extraction |
|  | `spec-reviewer` agent, generalized (entity model read from repo glossary) (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | template extraction |
|  | `bootstrap` skill: inspect → interview → copy → generate → verify (@main) | Done — gate recorded 2026-06-11: check-fast: PASS; smoke bootstrap of /tmp/wclip green end-to-end | `roadmap/specs/foundry-core/` | template extraction |
|  | `update` skill: version-marker diff + refresh (@main) | Done — gate recorded 2026-06-11: check-fast: PASS; smoke update of /tmp/wclip green (legacy backfill, refresh, customization protection, seed announce) | `roadmap/specs/foundry-core/` | bootstrap skill |
|  | Evals L1–L2: fixtures (Rust CLI, Python service, TS monorepo), harness, seeded defects, gate-discrimination checks (@main) | Done — 2026-06-11: full headless sweep green — python-service 51/51, rust-cli 47/47, ts-monorepo 46/46, update-eval 11/11; check-fast: PASS | `roadmap/specs/foundry-core/` | bootstrap skill |
|  | Evals L3: spec-reviewer precision/recall suite; lifecycle artifact checks (@main) | Done — 2026-06-12: reviewer-eval mean recall 0.967, 0 decoys; lifecycle-eval 7/7; plugin bumped to v1.0.0 (AC-2.3) | `roadmap/specs/foundry-core/` | Evals L1–L2 |
|  | COE mechanism: template (landed Wave 2), promote-upstream flow, eval-accretion rule (@main) | Done — gate recorded 2026-06-11: check-fast: PASS | `roadmap/specs/foundry-core/` | plugin skeleton |
|  | Reference-repo retrofit: consume foundry, move generic skill content upstream, keep domain-specific skills local | Backlog | spec to write | bootstrap skill |

### Epic 1 — Navigation eval + correctness/cost insight

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | navigation-eval spec: requirements + design + tasks | Done — approved 2026-06-13 (spec-reviewer applied) | `roadmap/specs/navigation-eval/` | — |
| nav-eval-harness | Nav-eval harness: fixture (gold span + decoys, 3 doc sizes), arms (full-load / native / knowledge.py), grader, token capture | Validating — built, gate green, live pilot N=1 ran | `roadmap/specs/navigation-eval/` | spec approval |
| nav-cost-viz | Correctness-vs-context-cost visualization (SVG plotter, reusable) | Validating — built + unit-tested; nav chart generated. Cross-eval token wiring (reviewer/bootstrap/lifecycle) still TODO | `roadmap/specs/navigation-eval/` | token capture |
| nav-pilot-finding | Pilot finding (N=1): all arms answer correctly (fixture non-discriminating on correctness); content loaded native ~201 < disclosure ~1.2k < full-load ~13k → disclosure protocol not necessary. Caveats: N=1, recall metric + arm enforcement need work | Validating | `roadmap/specs/navigation-eval/` | harness |
| nav-breadth-sweep | Breadth sweep + hybrid arm: corpus-size fixture, 5 arms (incl. hybrid grep+knowledge.py), cost-vs-size crossover chart | Validating — live sweep N=1 (5/25/100) done. Finding: all arms correct at every size; native grep leanest (~219 @100) while the knowledge.py catalog (`list`) is O(N), the most expensive (~1439 @100) → disclosure does NOT pay off for greppable lookups. Untested regime: non-greppable / browse-by-topic queries | `roadmap/specs/navigation-eval/` | nav-eval harness |

### Epic 2 — Knowledge format (OKF alignment)

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | okf-alignment spec: requirements + design + tasks | Done — approved 2026-06-14 (spec-reviewer applied) | `roadmap/specs/okf-alignment/` | — |
| okf-migration | OKF migration: `type` field, knowledge/concept vocabulary, `knowledge.py`, reserved `index.md`/`log.md`, rule + glossary (@main) | Validating — in-tree migration complete; check-fast: PASS; full bootstrap/reviewer eval confirmation not recorded here | `roadmap/specs/okf-alignment/` | spec approval |

### Epic 3 — Migration-aware update

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | migration-aware-update spec: requirements + design + tasks | Done — approved 2026-06-14 (spec-reviewer applied) | `roadmap/specs/migration-aware-update/` | OKF alignment |
| mau-convention-plumbing | Convention plumbing: `conventionVersion` in manifest (bootstrap stamps) + migration registry (@main) | Validating — check-fast: PASS | `roadmap/specs/migration-aware-update/` | spec approval |
| mau-okf-playbook | OKF migration playbook + update pre-flight (detect → dry-run → branch → chain → no-regression → stamp) + deterministic preflight (@main) | Validating — check-fast: PASS; migration-eval okf 7/7 | `roadmap/specs/migration-aware-update/` | convention plumbing |
| mau-eval-safety-net | Eval safety net: harness + tier-1 fixtures (okf, legacy, dirty, red-gate) + chaining/idempotency (@main) | Validating — tier-1 behaviors verified (cold `claude -p` composite + Claude Code engine okf 7/7); unified headless capstone deferred (usage limit) | `roadmap/specs/migration-aware-update/` | OKF playbook |

### Epic 4 — Harness-agnostic foundry

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | harness-agnostic spec: requirements + design + tasks | Done — approved 2026-06-16 (spec-reviewer applied) | `roadmap/specs/harness-agnostic/` | migration-aware-update |
| ha-axis-a | Axis A — foundry runs under Codex: harness map, plugin-root fix, invocation neutralization, shared `spec-reviewer.md`, distribution (`.agents/plugins/` + `.codex-plugin/`) | Validating — gate green; `foundry@foundry` discovered live under codex | `roadmap/specs/harness-agnostic/` | spec approval |
| ha-axis-b | Axis B — bootstrap emits per-harness: interview question, conditional `CLAUDE.md`, rules → `rules/`, `.foundry/manifest.json` + `harnesses` | Validating — gate green; foundry self-host manifest present (T12 knowledge.py → BACKLOG) | `roadmap/specs/harness-agnostic/` | Axis A |
| ha-axis-c | Axis C — convention-3 retrofit migration + update read-path (new-then-legacy, no re-prompt, add-a-harness) | Validating — gate green | `roadmap/specs/harness-agnostic/` | Axis B |
| ha-evals-selfhost | Evals + self-host: manifest-enforcing readability eval + self-host convergence done; live matrix (codex/claude headless: bootstrap, migration, reviewer parity, dogfood) → BACKLOG | Validating — readability + convergence green; missing/mismatched manifest is now a failing eval case | `roadmap/specs/harness-agnostic/` | Axis C |

### Epic 5 — Harness deliberation

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| harness-deliberation-spec | harness-deliberation spec: requirements + design + tasks (@codex) | Validating — Wave 8 (v0.1.2) + Wave 9 (T34–T40) + issue #6 timeout-crash fix **shipped in v0.1.3** (Release PR #5 merged @ `802d731`; L3 gate green: reviewer-eval recall 1.0, lifecycle-eval PASS; #6 closed). Remaining: T1 maintainer approval | `roadmap/specs/harness-deliberation/` | harness-agnostic |

### Epic 6 — Self-improving loop

Cron-driven self-improvement: signals (evals, dogfood findings, GitHub issues) → human-gated
A/B consult → harness deliberation → spec → `code`. Built on two Tier-1 enablers that make
parallel agent work safe and verifiable.

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | spawn-isolation: worktree-per-session in the shared fresh-session runner (the parallel-safety enabler) + sandbox the evals | **Done** — shipped in v0.1.3 (#8 @ `0057800`); independently verified (check-fast PASS, hermetic, discrimination real); includes the `.git/config` corruption root-cause fix (GIT_DIR leak in check-fast) | `roadmap/specs/spawn-isolation/` | — |
| code-review | code-review: skill + numbered Review stage (Verify → Knowledge → Review → Finish); the green-but-wrong gate (complete-impl, docs-sync, robust tests, sensible defaults, simplicity) + an eval-gated cross-model drop-only refuter | **In progress** — design approved; building end-to-end (Track A, off `main`) | `roadmap/specs/code-review/` | spawn-isolation |
| lifecycle-autonomy | lifecycle-autonomy: an autonomy dial for the `code` lifecycle — one level (Supervised/Guided/Autonomous) + a stop-point; set once at Frame, harness-aware (`/loop`, Codex `/goal`) (@claude, branch: feat/autonomy-dogfood) | Validating — built + gate-green (spec CLEAN; reference + code-skill hooks + static test + glossary); behavioral proof (T5): the e2e autonomous mode mechanically asserts the AC-2.4 invariant (main untouched — features integrate on a non-default branch), the named stop-point, and the no-progress guard, exercised by the Codex dogfood | `roadmap/specs/lifecycle-autonomy/` | — |
|  | reviewer-eval repoint: point `evals/harness/reviewer-eval.sh` off the removed `agents/spec-reviewer.md` at the `spec-review` skill | **Done** — shipped in v0.1.3 (#7); reviewer-eval green (recall 1.0, 0 decoys) + a missing-file guard | spec note | — |
| self-improving-loop | self-improving loop S1–S4: signal store → proposer cron → A/B consult UI → deliberate→spec→code pipeline | **In progress** — loop-spine deliberated; **S1 (signal store) spec being authored** (Track B, off `main`); two-zone storage decided; S2–S4 follow (S4 needs code-review) | spec to write | spawn-isolation, code-review |
|  | issue-triage: GitHub issues as a signal source — host cron ingests read-only → durable triage ledger → human whether/how consult → mechanically-gated `issue-act` | Planned — design done (deliberated); spec after loop S1+S3 | spec to write | self-improving loop S1+S3 |
|  | AppendOnlyStore extraction: extract the broker's append-only / immutable-payload / rebuildable-view store as a shared module for S1 to reuse | Planned — deferral condition met (0.1.3 shipped); separate refactor PR before the S1 build | — | harness-deliberation |
|  | US-7 eval-sandbox tripwire: mount `guard_real_config` as a tripwire at the eval entrypoints | Planned — low urgency (corruption root cause already fixed in check-fast); fold into the code-review wave or a small PR | `roadmap/specs/spawn-isolation/` | spawn-isolation |
|  | external telemetry + anonymization: opt-in conversation contribution + anonymization core + adversarial leakage eval | Backlog — deferred until the internal loop is proven; seam = `source_kind` on signal ingest | spec to write | self-improving loop |
|  | design diagrams convention: Mermaid architecture/class diagrams in `design.md`, reviewed by spec-review (design-time) + code-review docs-sync (build-time) | **Done** — shipped in v0.1.3 (#7): convention in the spec-format seed + SI/CR diagrams; code-review docs-sync (AC-3.5) enforces diagram↔code | `roadmap/specs/README.md` | — |
|  | vitepress Mermaid rendering: enable the Mermaid plugin so `design.md` diagrams render in the doc site | Backlog — small build-config; diagrams already render on GitHub | spec note | design diagrams convention |
| card-ids | Card Ids: unique gate-enforced `Id` column per board card + `check-board.py` lint (@claude, branch: card/card-ids, wt: /Users/bmransom/workplace/foundry-card-ids) | Validating — built, reconciled onto v0.1.8; `check-fast: PASS`; `SPEC_REVIEW: CLEAN` + `CODE_REVIEW: PASS` (fresh context); awaiting PR merge | `roadmap/specs/card-ids/` | spawn-isolation |
|  | branch protection on main: require a PR + green `check-fast` before merge | **Done** — enabled 2026-06-20: require a PR + green `gate`, enforced on everyone (incl. admins/agents) | — | spawn-isolation |
