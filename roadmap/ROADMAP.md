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
  In progress / Validating), enforced by `scripts/check-board.py` in the gate.
- **Claim a card by creating its `card/<id>` branch** and `wt/<id>` worktree off the
  default branch (`git worktree add -b card/<id> wt/<id> origin/<default>`); the branch's
  existence (`git worktree list`; the remote branch once pushed) is the claim — first claim
  wins. Don't commit a claim to the default branch; a card's board status rides the work's PR.
- Status flow: `Backlog → Ready → In progress → Done` (+ `Planned`, `Blocked` as a flag,
  `Superseded` terminal). `Validating` is **reserved** for a card that still needs a named
  post-merge check (e.g. a live verification) before `Done` — not a step every card passes.
- **`Done` = merged to the default branch with the gate green** — the merged PR's gate run
  is the recorded PASS; set `Done` in the merging PR, never a separate follow-up. (Release
  version is a separate axis: release-please / CHANGELOG, not the board.)

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
| nav-eval-harness | Nav-eval harness: fixture (gold span + decoys, 3 doc sizes), arms (full-load / native / knowledge.py), grader, token capture | Done — built, gate green, live pilot N=1 ran | `roadmap/specs/navigation-eval/` | spec approval |
| nav-cost-viz | Correctness-vs-context-cost visualization (SVG plotter, reusable) | Done — built + unit-tested; nav chart generated. Cross-eval token wiring (reviewer/bootstrap/lifecycle) still TODO | `roadmap/specs/navigation-eval/` | token capture |
| nav-pilot-finding | Pilot finding (N=1): all arms answer correctly (fixture non-discriminating on correctness); content loaded native ~201 < disclosure ~1.2k < full-load ~13k → disclosure protocol not necessary. Caveats: N=1, recall metric + arm enforcement need work | Done | `roadmap/specs/navigation-eval/` | harness |
| nav-breadth-sweep | Breadth sweep + hybrid arm: corpus-size fixture, 5 arms (incl. hybrid grep+knowledge.py), cost-vs-size crossover chart | Done — live sweep N=1 (5/25/100) done. Finding: all arms correct at every size; native grep leanest (~219 @100) while the knowledge.py catalog (`list`) is O(N), the most expensive (~1439 @100) → disclosure does NOT pay off for greppable lookups. Untested regime: non-greppable / browse-by-topic queries | `roadmap/specs/navigation-eval/` | nav-eval harness |

### Epic 2 — Knowledge format (OKF alignment)

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | okf-alignment spec: requirements + design + tasks | Done — approved 2026-06-14 (spec-reviewer applied) | `roadmap/specs/okf-alignment/` | — |
| okf-migration | OKF migration: `type` field, knowledge/concept vocabulary, `knowledge.py`, reserved `index.md`/`log.md`, rule + glossary (@main) | Done — in-tree migration complete; check-fast: PASS; full bootstrap/reviewer eval confirmation not recorded here | `roadmap/specs/okf-alignment/` | spec approval |
| knowledge-skill | knowledge skill: the judgment layer `code` Stage 5 has no skill for — home selection (glossary term / concept / log / `AGENTS.md`), the four OKF types, provenance + citation-anchoring, append-don't-overwrite, and coherence (orphan / stale / missing-page / contradiction). Grounds on Google's OKF + Karpathy's LLM-Wiki, tightened for a single-repo engineering KB; a guidance skill Stage 5 defers to (+ progressive disclosure + a grounded "Differences from OKF" note) | **Done** — built on `card/knowledge-skill`, `check-fast: PASS`, `CODE_REVIEW: PASS` (fresh context); OKF-divergence table verified vs `knowledge.py`/config | `roadmap/specs/knowledge-skill/` | okf-migration |

### Epic 3 — Migration-aware update

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | migration-aware-update spec: requirements + design + tasks | Done — approved 2026-06-14 (spec-reviewer applied) | `roadmap/specs/migration-aware-update/` | OKF alignment |
| mau-convention-plumbing | Convention plumbing: `conventionVersion` in manifest (bootstrap stamps) + migration registry (@main) | Done — check-fast: PASS | `roadmap/specs/migration-aware-update/` | spec approval |
| mau-okf-playbook | OKF migration playbook + update pre-flight (detect → dry-run → branch → chain → no-regression → stamp) + deterministic preflight (@main) | Done — check-fast: PASS; migration-eval okf 7/7 | `roadmap/specs/migration-aware-update/` | convention plumbing |
| mau-eval-safety-net | Eval safety net: harness + tier-1 fixtures (okf, legacy, dirty, red-gate) + chaining/idempotency (@main) | Done — tier-1 behaviors verified (cold `claude -p` composite + Claude Code engine okf 7/7); unified headless capstone deferred (usage limit) | `roadmap/specs/migration-aware-update/` | OKF playbook |
| update-gate-sync | update-gate-sync: gate tools self-declare via a `# foundry-gate-tool:` marker so both `bootstrap` and `update` wire them (no drifting hardcoded lists) — closing the gap where `update` delivers `check-board.py`/`prose-lint.py` as inert files the gate never runs; + a `card-ids` migration (conv 4) backfilling the now-required board `Id`s; + a self-host lint (gate-sync dogfooded) so Foundry's own gate fails on an unwired gate tool or a missed migration — a gate, not a `code-review` reminder | **Done** — built on `card/update-gate-sync`, `check-fast: PASS`, `CODE_REVIEW: PASS` (fresh context); self-host lint green on Foundry (conv 4) | `roadmap/specs/update-gate-sync/` | mau-okf-playbook, card-ids |

### Epic 4 — Harness-agnostic foundry

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
|  | harness-agnostic spec: requirements + design + tasks | Done — approved 2026-06-16 (spec-reviewer applied) | `roadmap/specs/harness-agnostic/` | migration-aware-update |
| ha-axis-a | Axis A — foundry runs under Codex: harness map, plugin-root fix, invocation neutralization, shared `spec-reviewer.md`, distribution (`.agents/plugins/` + `.codex-plugin/`) | Done — gate green; `foundry@foundry` discovered live under codex | `roadmap/specs/harness-agnostic/` | spec approval |
| ha-axis-b | Axis B — bootstrap emits per-harness: interview question, conditional `CLAUDE.md`, rules → `rules/`, `.foundry/manifest.json` + `harnesses` | Done — gate green; foundry self-host manifest present (T12 knowledge.py → BACKLOG) | `roadmap/specs/harness-agnostic/` | Axis A |
| ha-axis-c | Axis C — convention-3 retrofit migration + update read-path (new-then-legacy, no re-prompt, add-a-harness) | Done — gate green | `roadmap/specs/harness-agnostic/` | Axis B |
| ha-evals-selfhost | Evals + self-host: manifest-enforcing readability eval + self-host convergence done; live matrix (codex/claude headless: bootstrap, migration, reviewer parity, dogfood) → BACKLOG | Done — readability + convergence green; missing/mismatched manifest is now a failing eval case | `roadmap/specs/harness-agnostic/` | Axis C |

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
| code-review | code-review: skill + numbered Review stage (Verify → Knowledge → Review → Finish); the green-but-wrong gate (complete-impl, docs-sync, robust tests, sensible defaults, simplicity) + an eval-gated cross-model drop-only refuter | Done — shipped on `main` (`plugins/foundry/skills/code-review/`; gate tests green: `code_review_*`, `score_review`); inner/outer convergence loops + cross-model refuter landed | `roadmap/specs/code-review/` | spawn-isolation |
| lifecycle-autonomy | lifecycle-autonomy: an autonomy dial for the `code` lifecycle — one level (Supervised/Guided/Autonomous) + a stop-point; set once at Frame, harness-aware (`/loop`, Codex `/goal`) (@claude, branch: feat/autonomy-dogfood) | Done — built + gate-green (spec CLEAN; reference + code-skill hooks + static test + glossary); behavioral proof (T5): the e2e autonomous mode mechanically asserts the AC-2.4 invariant (main untouched — features integrate on a non-default branch), the named stop-point, and the no-progress guard, exercised by the Codex dogfood | `roadmap/specs/lifecycle-autonomy/` | — |
|  | reviewer-eval repoint: point `evals/harness/reviewer-eval.sh` off the removed `agents/spec-reviewer.md` at the `spec-review` skill | **Done** — shipped in v0.1.3 (#7); reviewer-eval green (recall 1.0, 0 decoys) + a missing-file guard | spec note | — |
| self-improving-loop | self-improving loop S1–S4: signal store → proposer cron → A/B consult UI → deliberate→spec→code pipeline | **In progress** — loop-spine deliberated; **S1 (signal store) spec being authored** (Track B, off `main`); two-zone storage decided; S2–S4 follow (S4 needs code-review) | spec to write | spawn-isolation, code-review |
|  | issue-triage: GitHub issues as a signal source — host cron ingests read-only → durable triage ledger → human whether/how consult → mechanically-gated `issue-act` | Planned — design done (deliberated); spec after loop S1+S3 | spec to write | self-improving loop S1+S3 |
|  | AppendOnlyStore extraction: extract the broker's append-only / immutable-payload / rebuildable-view store as a shared module for S1 to reuse | Planned — deferral condition met (0.1.3 shipped); separate refactor PR before the S1 build | — | harness-deliberation |
|  | US-7 eval-sandbox tripwire: mount `guard_real_config` as a tripwire at the eval entrypoints | Planned — low urgency (corruption root cause already fixed in check-fast); fold into the code-review wave or a small PR | `roadmap/specs/spawn-isolation/` | spawn-isolation |
|  | external telemetry + anonymization: opt-in conversation contribution + anonymization core + adversarial leakage eval | Backlog — deferred until the internal loop is proven; seam = `source_kind` on signal ingest | spec to write | self-improving loop |
|  | design diagrams convention: Mermaid architecture/class diagrams in `design.md`, reviewed by spec-review (design-time) + code-review docs-sync (build-time) | **Done** — shipped in v0.1.3 (#7): convention in the spec-format seed + SI/CR diagrams; code-review docs-sync (AC-3.5) enforces diagram↔code | `roadmap/specs/README.md` | — |
|  | vitepress Mermaid rendering: enable the Mermaid plugin so `design.md` diagrams render in the doc site | Backlog — small build-config; diagrams already render on GitHub | spec note | design diagrams convention |
| card-ids | Card Ids: unique gate-enforced `Id` column per board card + `check-board.py` lint | **Done** — merged via #31; CI `check-fast: PASS` (the recorded gate); `SPEC_REVIEW: CLEAN` + `CODE_REVIEW: PASS` (fresh context) | `roadmap/specs/card-ids/` | spawn-isolation |
| worktree-per-card | worktree-per-card: the card's git lifecycle — one worktree per card (`card/<id>` + `wt/<id>`) off the default branch, commit freely, **`Done` = merged** (set in the merging PR); reserves `Validating` | **Done** — merged to `main` with CI `check-fast: PASS` (the recorded gate); `SPEC_REVIEW: CLEAN` + `CODE_REVIEW: PASS` (fresh context) | `roadmap/specs/worktree-per-card/` | card-ids, lifecycle-autonomy |
| review-convergence | review-convergence: severity-gate `spec-review` (blocking/advisory), blind re-review, objective prose → a deterministic linter, + a shared cross-family review pass (DROP for code-review / UNION for spec-review, eval-gated); closes the primed-`CLEAN` COE | In progress — spec approved; implementing on `card/review-convergence` | `roadmap/specs/review-convergence/` | code-review |
| reviewer-effort | reviewer-effort: a neutral `--effort`/`--model` knob on the fresh-session spawn, mapped per harness (claude `--effort` / codex `-c model_reasoning_effort=`), threaded so the adversarial cross-family pass runs at higher effort than the primary — eval-gated | Planned — design pending approval | `roadmap/specs/reviewer-effort/` | review-convergence |
| review-default-placement | code-review's defaults dimension checks **placement**, not just sensibility: a value defaults once at the boundary (highest layer the caller could supply it), mandatory downstream — flag a buried or scattered default (no single source of truth). Generalizes the reviewer-effort default-at-the-top principle; seeded eval (V6) | **Done** — built on `card/review-default-placement`, `check-fast: PASS`, `CODE_REVIEW: PASS` (fresh context) | — | code-review |
| review-coverage | code-review coverage **beyond the diff**: Complete-implementation flags a half-applied change (a parallel call site / enum case / mirrored file updated in one place but not its twin — cite the twin); a new Dead/duplicate dimension flags a symbol the change orphaned (zero refs — cite the grep; a public API is not dead) and copy-paste past the rule of three (coincidental 2× is not DRY). Precision-first carve-outs; seeded V7/V8/V9 + decoys D8/D9/D10 | **Done** — built on `card/review-coverage`, `check-fast: PASS`, `CODE_REVIEW: PASS` (fresh context) | — | code-review |
| refuter-reproduce | refuter reproduces native runtime findings via `lldb`: for a high-severity suspected runtime fault in a buildable native target (C/C++/Rust/Swift), the cross-family refuter (the adversary) invokes the `debug` skill to set a breakpoint and reproduce — **keep the finding only if it reproduces, drop it otherwise** (proof-by-reproduction). Composes the `debug` skill + the DROP-only refuter; opt-in, native-only, needs a runnable repro. Eval: reproduce-or-drop kills a non-reproducing finding, keeps a reproducing one | Backlog — design pending; spec to write | spec to write | code-review, debug-skill |
| verify-by-execution | the umbrella for "false feedback is the worst": a code-review finding **checkable by running** — a claimed failing test, a wrong runtime value, an unreachable path — SHALL be **run** before it's posted (the existing test, a one-off snippet, `pytest`/`node`, or `lldb` for native), not just read. A finding that can't be executed is stamped a **hypothesis** (advisory / lower-confidence); a **blocking** finding must be in the *proven* column — don't let an unverified claim block a PR. The adversary (refuter) is the home (it already gates "is this real?"). Scope: verify the high-severity / cheaply-runnable findings, not every advisory nit. `refuter-reproduce` is the native/`lldb` instance of this | Backlog — design pending; spec to write | spec to write | code-review |
| policy-constant-rationale | sensible policy constants (timeouts, retries, limits, TTLs, page sizes): "sensible" is domain knowledge a static reviewer can't judge. (a) code-review flags a policy constant with **no recorded rationale** (require a source — the spec, a cited SLA, a comment); (b) at Build, the author **confirms a new domain-sensitive constant with the user**, governed by the autonomy dial (Supervised/Guided ask), and records the rationale in `design.md`. The gate enforces the rationale *exists*, not the value's correctness | Backlog — design pending; spec to write | spec to write | code-review, lifecycle-autonomy |
| pr-deliberation | agents converse via PR comments, not locally: run `code-review` (or the cross-family reviewer + refuter) against an **open GitHub PR** — each finding posts as a PR review comment anchored to `file:line`, the cross-family adversary (e.g. Codex) replies KEEP/DROP with evidence on the thread, and the human can chime in inline. Replaces the local `.foundry/reports/` transcript with a durable, visible, human-in-the-loop PR conversation (`gh pr review` / `gh api` to post + read comments). Distinct from `ultrareview` (reviews a PR but doesn't converse in joinable threads). A PR-comment **transport** over `code-review`'s existing find→refute→verdict logic; reuses the single-asymmetric DROP-only refuter (not a debate); never auto-approves. (Conceptual sibling of `harness-deliberation`, generalized to a PR transport — a later card.) | Planned — design pending approval; spec on `card/pr-deliberation` | `roadmap/specs/pr-deliberation/` | code-review |
| pr-review-runner | push-trigger for `pr-deliberation`: run Foundry's review (reviewer + cross-family refuter) **headless on a self-hosted GitHub Actions runner** (your own server), fired by a PR mention / slash-command (`issue_comment`), delivering via the `pr-deliberation` transport. **Subscription auth, not API** — a Claude Code OAuth token (`claude setup-token`) + a Codex subscription login on the runner draw on the Max/ChatGPT plans (no per-token billing; both CLIs on one runner for the cross-family pass). **Hardening is mandatory** (self-hosted runners are not ephemeral; `issue_comment` is an injection vector that can exfil secrets): private repo, member-only trigger, never run fork PRs, isolated/ephemeral runner, sanitize comment text, Claude Code ≥ the /proc-leak fix. Trade-off: automation shares the subscription's interactive rate limits | Backlog — research done; spec to write | spec to write | pr-deliberation, harness-agnostic |
|  | branch protection on main: require a PR + green `check-fast` before merge | **Done** — enabled 2026-06-20: require a PR + green `gate`, enforced on everyone (incl. admins/agents) | — | spawn-isolation |

### Epic 7 — Developer experience & extensibility

Surfaces that make a foundry repo pleasant to live in (a native-code debugger skill) and that
let consuming repos reshape the SDLC without forking (configurable skill hooks).

| Id | Work | Status | Spec | Depends on |
|---|---|---|---|---|
| debug-skill | debug skill: drive `lldb` to debug native code (C/C++/Rust/Swift) — set/clear breakpoints, step (`step`/`next`/`finish`/`continue`), inspect frames, variables, and backtraces (`frame`, `p`, `bt`), attach to a live process or load a core; harness-agnostic, `gdb` a documented sibling (one skill + an lldb↔gdb map) | **Done** — merged via #43 (`check-fast: PASS`); live `lldb` eval **passed** — a skill-guided agent localized the seeded heap OOB write via lldb (conditional breakpoint → `frame variable` → ASan trap at `prog.c:8`), the static-only control failed (discrimination confirmed) | `roadmap/specs/debug-skill/` | — |
| skill-hooks | configurable skill hooks: let a consuming repo customize the SDLC at stage boundaries (a custom Verify gate, a Finish step, …) without forking — a **skill-run stage-hook convention** (`.foundry/hooks/<stage>.{pre,post}.sh`, `.foundry/hooks.json` opt-in), harness-agnostic by construction. Research (2026-06-28): no `pi.dev` needed; per-harness native-hook adapters **rejected** (wrong abstraction — SDLC stages are not tool-events). Tool-level gating is delegated to the harness's native hooks, not rebuilt. **Parked**: *guaranteeing* pre/post triggering can't ride agent discretion (advisory-strength) — the industry-consensus answer is a deterministic lifecycle driver (code-as-orchestrator, like the convergence hooks already are), a bigger architectural call (see the spec's Open question) | Backlog — spec drafted; parked on the triggering-guarantee question | `roadmap/specs/skill-hooks/` | harness-agnostic |
