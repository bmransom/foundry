<!-- foundry-seed: log v1 -->

# Knowledge log

Changes to the knowledge base, newest first. A reserved OKF file — no frontmatter.

## 2026-07-03

- **Update** Added two glossary conventions: a **Bounded contexts** section (document sub-domain boundaries where a term's meaning differs, like the ubiquitous language and entity model) and an **alphabetical** ordering nudge for canonical terms — glossary seed v2 + knowledge rubric. Prior art: DDD bounded contexts.
- **Update** Fixed `foundry bootstrap` stamping `conventionVersion` 5 while installing the conv-6 shim (`CONVENTION_VERSION` missed the cli-shim bump); added a drift guard test asserting it equals the registry head.
- **Update** Tightened the `performance`, `design-patterns`, and `naming-standards` skill descriptions after the codex triggering run flagged them over-broad (cloud-bill ops, feature brainstorming, UI translation) — a scoped exclusion on each to true intent.
- **Update** Tightened the `code` and `handoff` skill descriptions after a live codex triggering run (27/33) flagged them over-broad (`code` claimed generic coding; `handoff` a human QA hand-off) — scoped to a board-card lifecycle and agent-session continuity.
- **Update** Made the triggering eval harness-agnostic (`triggering-eval.sh --harness claude|codex`) — it was hardcoded to `claude -p` though v2 routes every other agent call through adapters; codex classifies via `codex exec --json`.
- **Update** Restored the interactive skill layer v2 (#70) deleted — `code`, `handoff`,
  `spec-review`, `code-review`, `knowledge` — as the supervised twin of the driver. The stage
  skills single-source their judgment from the new `foundry rubric <stage>` printer (one
  source, two consumers: driver compile + skill fetch), reached via the `.foundry/bin/foundry`
  shim. `handoff` restored near-verbatim (its `spawn-fresh-session.sh` runner survived the
  purge). No glossary rows — the skills are generic engineering practice.


- **New** Added **CLI shim** (`.foundry/bin/foundry`, conv 6 `foundry-cli-shim`): the
  repo-local, pin-free entry point every caller uses — the plugin ships skills, not the CLI,
  so a session (and the `code` skill) reaches the pinned CLI through the shim. Collapses the
  two-places pin [[Pinned run]]/pin-sync kept in step; extends **Pinned run**.
- **New** Added **Gate feedback** (closed-loop-control / CI failure-reporting prior art; extends
  **Gate**) for `roadmap/specs/gate-feedback/` — the driver's first production run halted on three
  blind, identically-prompted build retries; retries now carry the failed gate's evidence.

## 2026-07-02

- **New** Landed the eleven **foundry-v2** vocabulary terms deferred by `roadmap/specs/foundry-v2/design.md`
  §New vocabulary: **Driver**, **Harness adapter**, **Stage prompt**, **Stage rubric**, **Run
  ledger**, **Routing table**, **Pinned run**, **Materializer**, **Conformance fixture**, **Pytest
  repo fixture**, **Gate suite** — paying the provenance debt now that Waves 0–3 are code-complete
  rather than deferring further. **Conformance fixture** and **Pytest repo fixture** are explicit
  xUnit-family siblings of the existing **Fixture** row, scoped apart from it (adapter transcripts
  and test-local repos, not eval targets); **Gate suite** extends the existing **Gate** term;
  **Driver**'s debt term (`orchestrator (for the lifecycle stages)`) is scoped apart from
  **Broker**'s existing `orchestrator` debt term (harness-deliberation sequencing). No other
  existing rows changed.

## 2026-06-29

- **Update** knowledge-listing fidelity (`okf-listing-fidelity`): `knowledge/README.md` is now a
  reserved file (it was `srcExclude`d from the vitepress build yet listed → a dead sidebar link); the
  generated `index.md` declares `okf_version`; and `list`/`index.md`/sidebar order current concepts
  first, tagging non-current ones `(superseded)`/`(historical)`.

- **Validation** verify-by-execution's **native executor is live-proven**:
  `evals/harness/verify-exec-live.sh` builds the debug fixture with ASan + symbols and drives a
  **real `lldb` session** through `verify-finding.sh run native` — the seeded heap-OOB reproduces →
  **verified**, the fixed target (`i < n`) drops → **refuted**. The native path is no longer a stub
  (it runs an lldb-built repro check). Live eval (needs `lldb`/`cc`), kept out of the fast gate.

- **Convention** `code-review` verifies blocking findings **by execution**, not just reading
  (`verify-finding.sh`): the cross-model refuter *runs* a finding's check (its test, a repro
  snippet, or `lldb` via the `debug` skill) — **verified** may block, **refuted** drops,
  **un-runnable** demotes to advisory. Additive — single-harness keeps today's read-based blocking,
  no recall regression. Folds `refuter-reproduce` as the native executor. Hermetic
  `verify_finding_test.sh`; live `lldb`/test run deferred.

- **Convention** `code-review` gains coverage **beyond the diff**: **Complete implementation** now
  flags a **half-applied change** (a parallel call site / enum case / mirrored file updated in one
  place but not its twin — cite the twin), and a new **Dead / duplicate code** dimension flags a
  symbol the change orphaned (zero references — but a public API is not dead, cite the grep) and
  copy-paste past the rule of three (coincidental 2× is not DRY-violating). Eval: seeded V7 (ripple
  `expired` cache choice), V8 (dead `format_legacy_report`), V9 (duplicate `summarize_*_failure`) +
  decoys D8 (public-API-not-dead), D9 (coincidental).
- **Convention** `code-review`'s defaults dimension now checks **placement**, not just
  sensibility: a value should default once at the boundary (the highest layer the caller could
  supply it), with mandatory parameters downstream — the reviewer flags a buried or scattered
  default (no single source of truth), generalizing the `reviewer-effort` default-at-the-top
  principle. Eval: a seeded buried/scattered `partner_timeout` default (V6) in the `code-review`
  fixture.

## 2026-06-28

- **Update** Added the **`knowledge`** skill (`plugins/foundry/skills/knowledge/`): the
  KB-maintenance judgment `code` Stage 5 now defers to — home selection (glossary / concept /
  `log.md` / `AGENTS.md`), the four OKF types, provenance + citation-anchoring,
  append-don't-overwrite, coherence (orphan / stale / missing-page / contradiction), and
  progressive disclosure (`index.md` → `outline` → `section`). `references/okf.md` documents
  Foundry's divergences from Google's OKF (fixed types, required fields, strict lint, the
  `lifecycle` staleness field, append-only log); grounded in OKF + Karpathy's LLM-Wiki. No
  glossary row (generic KB practice).
- **Update** Added the **`Gate tool`** term and the `# foundry-gate-tool:` marker (a sibling of
  `foundry-template:` / `foundry-seed:`): a verbatim script self-declares that it belongs in the
  gate by carrying its literal gate line, so `bootstrap` and `update` wire every marked tool with
  no hardcoded list. A Foundry-local `check-gate-tools.sh` enforces the wiring + the
  registry-head == `conventionVersion` invariant (`update-gate-sync`).
- **Update** Added the **`debug`** skill (`plugins/foundry/skills/debug/`): drive `lldb` to
  localize a fault in native code (breakpoints, stepping, frame/variable/backtrace inspection,
  attach, cores); `gdb` is a documented sibling via an `lldb`↔`gdb` map. Generic debugger
  practice — **no glossary row** (prior art the LLDB/GDB docs; provenance in the SKILL header,
  mirroring `code-review`/`spec-review`). Discrimination is gate-proven by
  `evals/harness/test_grade_debug.py` (run via `tests/grade_debug_test.sh`): a debugger-used
  transcript passes, a static-only correct guess fails; the live `lldb` run is deferred.

- **Convention** `spec-review` is now **severity-gated** like `code-review`: findings carry
  `blocking`/`advisory`, the `FLAGGED:` footer carries the blocking ones, and `SPEC_REVIEW:
  CLEAN` means *no unresolved blocking finding* (advisory may remain). The convergence re-pass
  of both review skills is **blind** — never handed a summary of what changed. Objective
  filler is gated by `scripts/prose-lint.py` (a banned-phrase lint); **debt-term misuse stays
  a blocking judge call** — a build-time finding: the glossary scopes debt terms by context
  ("scaffold" only as a verb), so it cannot be deterministically linted. No `glossary.md` row
  (`blocking`/`advisory` are generic terms with prior art). Spec:
  `roadmap/specs/review-convergence/`; closes (when fully landed)
  `knowledge/review-convergence-coe.md`. The cross-family UNION pass (US-5) lands in a later
  wave, eval-gated.

## 2026-06-27

- **Convention** Redefined the **Done** board status and adopted the **worktree-per-card**
  working model (`roadmap/specs/worktree-per-card/`). A card runs in its own
  `card/<id>` worktree off the default branch, is committed freely as recoverable
  checkpoints, and is **Done when its branch merges to the default branch with the gate
  green** (set in the merging PR) — replacing "ask before every commit" and "Done = shipped
  in a release," and the Epic-0-vs-Epic-6 inconsistency. The claim signal is the
  `card/<id>` branch's existence; release/version tracking is a separate axis (changelog,
  not the board). Guarded by `tests/done_merged_docs_test.sh`. Prior art: trunk-based
  development (done = integrated to trunk).

## 2026-06-25

- **Fix** Bootstrap's `generate.md` vocab-lint guidance now scopes the generated
  `scripts/vocab-lint.sh` to **markdown prose** and excludes generated/dependency trees
  (`node_modules/`, `dist/`, lockfiles, the VitePress build). The lifecycle-e2e dogfood
  surfaced the gap: a fresh agent generated a recursive grep over `knowledge/` that
  false-matched the debt term `AI` inside `knowledge/package-lock.json`
  (`sponsors/ai`). The agent recovered, but the guidance now bakes the fix in so the
  next bootstrap gets it right unaided. The e2e harness gained a regression signal that
  flags a generated lint which fails to scope to prose.
- **New** Glossary terms **Autonomy level** and **Stop-point** for the `code` lifecycle's
  autonomy dial (`roadmap/specs/lifecycle-autonomy/`). The level (Supervised / Guided /
  Autonomous) decides who resolves a soft fork; the stop-point bounds an autonomous run.
  Set once at Frame, harness-aware (`/loop`, Codex `/goal`); the operational detail lives
  in `plugins/foundry/skills/code/references/autonomy.md`. Prior art: Codex approval modes
  + role-based agent-autonomy levels (autonomy level); the debugger breakpoint (stop-point).
- **Update** The **code-review** skill reached feature-complete (spec
  `roadmap/specs/code-review/` `SPEC_REVIEW: CLEAN`): a synchronous runner with inner
  review-convergence + outer fix-convergence loops, a cross-model DROP-only refuter with
  footer-algebra recompute, agent-calibration guardrails (evidence-or-drop,
  silence-beats-noise, no-invented-requirements, leave-style-to-the-linter) + spec
  grounding, manifest-derived refuter families via `--harness`, and the shared
  `resolve_base` diff range. No new glossary concepts — generic prior art; provenance in
  the SKILL header. The L3 eval + the hermetic A/B gate decide refuter enablement.
- **Update** Added the **Card id** term — a card's unique, slug-safe handle in the
  board's `Id` column, enforced by `scripts/check-board.py` — for the card-ids feature
  (`roadmap/specs/card-ids/`).

## 2026-06-24

- **Convention** Wiring a PostToolUse convergence trigger (`spec-convergence-posttooluse.sh`,
  and a future `code-review-posttooluse.sh`): scope it with BOTH layers — the Claude Code
  hook `if` field (native path filter, e.g. `Edit(/roadmap/specs/**/*.md)|Write(…)|MultiEdit(…)`;
  the `matcher` matches tool names only) AND the adapter's own in-script path filter. The
  `if` field is Claude-Code-only, so the in-script filter is the harness-agnostic correctness
  guarantee (Codex has no `if`). Verify the installed Claude Code version supports `if` before
  relying on it. Source: code.claude.com/docs/en/hooks.md#path-based-filtering.

## 2026-06-20

- **Update** Registered the **Code-review eval (L3)** in **Validation**
  (`evals/harness/code-review-eval.sh`) — manual, required green for a version
  bump; the A/B arm gates cross-model refuter enablement. No glossary entry: code
  review is generic prior art, provenance lives in the SKILL header (mirroring
  `spec-review`).

## 2026-06-19

- **Update** Added **Session storage tier** provenance for harness deliberation
  Tier 1 event ledger, Tier 2 immutable payloads, and Tier 3 rebuildable views.
- **Update** Recorded the opt-in harness deliberation live smoke command and
  PASS result in **Validation**.
- **Update** Clarified that `harness-status.py` is the stored-result label for
  **Harness availability**, not a separate glossary concept.
- **Update** Added harness-deliberation vocabulary: **Harness availability**, **Broker**, **Harness deliberation** (multi-agent debate/deliberation prior art, Foundry harness terminology), **Participant**, **Mediator**, and **Deferred dissent** for the new `roadmap/specs/harness-deliberation/` spec.

## 2026-06-16

- **Update** Added the **harness** term (an AI coding tool that runs foundry's skills; agent-harness-engineering vocabulary) and pointed the **Manifest** and **Convention version** entries at `.foundry/manifest.json` with the harness set — Wave 1 of harness-agnostic (`roadmap/specs/harness-agnostic/`).

## 2026-06-14

- **Update** Aligned the knowledge base to the Open Knowledge Format: `type` frontmatter (was `kind`), reserved `index.md` and `log.md`, and the `knowledge` tool and vocabulary.
