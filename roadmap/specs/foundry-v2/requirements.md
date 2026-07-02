---
title: foundry-v2 requirements
description: Rebuild foundry's chassis as a standalone CLI — deterministic lifecycle driver, harness adapters as data, run ledger, pinned-run distribution.
---

> **Status:** Done (2026-07-02) — spec approved and implemented (Epic 8); tracked on the [board](../../ROADMAP.md).

# foundry-v2 — requirements

## Overview

v1 proved the conventions; the chassis is the weak layer. Every mechanically decidable
operation — bootstrap's copy, update's migrations, gate sequencing, fresh-session
spawning — runs as prose an LLM interprets, with scripts as helpers. The evidence is
in-repo: the byte-identity gate exists because prose-driven copying is unreliable;
`skill-hooks` parked because gate triggering "can't ride agent discretion"; the tmux
fresh-session runner is the most fragile mechanism shipped.

v2 inverts the ratio: **deterministic core in code, judgment in skills.** A standalone
`foundry` CLI (Python, uv, installed from this repo by git tag) owns the lifecycle
driver, the gate suite, harness adapters, the run ledger, and (later) the
materializer.
Skills keep the judgment: interviews, design, build, review, knowledge placement.

The audience is the maintainer first, teammates later. Conventions therefore stay
repo-resident — `AGENTS.md`, board, glossary, gates readable by any harness's agent with
no foundry installation; the CLI is leverage, not a reading prerequisite. v2 is built
fresh in this repo, driver-first; git history is the fallback.

Decisions fixed with the maintainer (2026-07-02) are recorded in `design.md` §Decisions.

## User stories

### US-1 — Lifecycle driver

As the maintainer, I want the `code` lifecycle enforced by a deterministic driver, so a
gate cannot be rationalized past and every stage transition is recorded.

- AC-1.1 WHEN `foundry run <card-id>` starts, THE SYSTEM SHALL resolve the card from
  `roadmap/ROADMAP.md`, create or reuse its `card/<id>` branch and `wt/<id>` worktree off
  the default branch, and append a `run_started` event to the run ledger.
- AC-1.2 WHEN a stage completes, THE SYSTEM SHALL evaluate that stage's gate in code and
  SHALL NOT enter the next stage until the gate passes.
- AC-1.3 WHEN a judgment stage runs, THE SYSTEM SHALL invoke the routed harness headlessly
  with the stage prompt and capture its structured output, token usage, and exit status.
- AC-1.4 WHEN a stage's gate fails 3 consecutive times (`RETRY_CAP`, a fixed constant in
  `machine.py`), THE SYSTEM SHALL halt the run with a `run_halted` event naming the
  failing gate — never auto-pass.
- AC-1.5 WHERE `--interactive` is set, THE SYSTEM SHALL open the routed harness
  interactively inside the stage's worktree and resume deterministic gate evaluation when
  the session exits.
- AC-1.6 WHEN `foundry run --resume <run-id>` is invoked after an interrupted run, THE
  SYSTEM SHALL resume from the last recorded stage boundary in the ledger.
- AC-1.7 WHILE a run is active, THE SYSTEM SHALL honor the configured autonomy level and
  stop-point: at each boundary the level maps to (ask / proceed), and reaching the
  stop-point ends the run with a `run_completed` event.
- AC-1.8 WHEN the driver finishes a run, THE SYSTEM SHALL have made no commit to the
  default branch and no push anywhere (pushing stays a human act).
- AC-1.9 WHERE `.foundry/hooks/<stage>.pre.sh` or `.foundry/hooks/<stage>.post.sh`
  exists and is executable, THE SYSTEM SHALL run it at that stage boundary in the run's
  worktree: a non-zero pre hook blocks stage entry, a non-zero post hook fails the
  stage's gate; both outcomes are ledger events. (Delivers the `skill-hooks` convention
  with the opt-in simplified to the executable bit — no `hooks.json`; the driver is the
  triggering guarantee that card parked on.)

### US-2 — Harness adapters as data

As the maintainer, I want each harness expressed as a data file plus conformance
fixtures, so adding a harness is a config file and a green fixture run, not new code.

- AC-2.1 WHEN the CLI loads, THE SYSTEM SHALL read each harness adapter (TOML shipped in
  the package) declaring: instruction-file mapping, headless command template,
  interactive command template, model and effort flag mappings, and the named output
  parser.
- AC-2.2 WHEN `foundry doctor` runs, THE SYSTEM SHALL check every adapter referenced by
  the repo's routing table for harness availability (e.g. command present, auth valid);
  conformance fixtures (recorded transcripts) are validated by this repo's test suite,
  which ships no fixtures in the package.
- AC-2.3 THE SYSTEM SHALL ship `claude-code` and `codex` adapters; a third harness SHALL
  require only a new adapter file, a parser if its output format is new, and fixtures.
- AC-2.4 THE SYSTEM SHALL keep every convention a consumer repo depends on in repo files
  (`AGENTS.md`, board, glossary, gate definitions), such that an agent on any harness can
  work in the repo with no foundry installation.

### US-3 — Model routing

As the maintainer, I want per-stage model routing with shipped defaults, so mechanical-leaning
stages run on cheap models and design/review stages on frontier models — and I can
override it.

- AC-3.1 WHEN a judgment stage is invoked, THE SYSTEM SHALL resolve (harness, model,
  effort) with precedence: CLI flag > repo `.foundry/config.toml` routing table > shipped
  defaults.
- AC-3.2 THE SYSTEM SHALL record the resolved (harness, model, effort) and measured token
  usage in the stage's ledger events.
- AC-3.3 WHERE a harness does not support an effort parameter, THE SYSTEM SHALL omit it
  rather than fail.

### US-4 — Run ledger with cost

As the maintainer, I want every run to emit structured events including cost, so the
self-improving loop derives from records — and routing choices are judged by data.

- AC-4.1 WHEN any run starts, THE SYSTEM SHALL append events to
  `.foundry/runs/<run-id>/events.jsonl` (gitignored), one JSON object per line,
  append-only.
- AC-4.2 THE SYSTEM SHALL give every event the wide-event fields: `run_id`, `card_id`,
  `stage`, `event`, `ts`, plus per-stage `harness`, `model`, `effort`, `input_tokens`,
  `output_tokens`, `cost_usd`, `duration_s`, and gate outcomes.
- AC-4.3 WHEN `foundry runs list` is invoked, THE SYSTEM SHALL list past runs with
  per-run cost and outcome (`gh run list` prior art for the noun-verb form).
- AC-4.4 WHEN `foundry runs show <run-id>` is invoked, THE SYSTEM SHALL print the run's
  stage table.

### US-5 — Pinned-run distribution

As a teammate on a consumer repo, I want gates and tools to run at a repo-pinned foundry version with
no vendored scripts and no install step, so every clone and CI runs the same tooling.

- AC-5.1 THE SYSTEM SHALL read the pinned version (a git tag of this repo) from
  `.foundry/config.toml`; `foundry gate`, hooks, and CI SHALL be invocable via a single
  pinned command (`uvx --from git+<repo-url>@<tag> foundry …`) with no prior install.
- AC-5.2 WHEN `foundry gate` runs in a consumer repo, THE SYSTEM SHALL execute the gate
  suite (board check, prose lint, knowledge check, plus the repo's own gate commands from
  config) and exit non-zero on any failure, printing one `gate: PASS|FAIL` line last.
- AC-5.3 WHEN the pinned-run convention break ships, THE SYSTEM SHALL provide a migration
  that removes vendored gate scripts, rewrites `.githooks/pre-push` and CI to the pinned
  command, and bumps the convention version.
- AC-5.4 WHEN the installed CLI version differs from the repo's pin, THE SYSTEM SHALL
  warn on every command and `foundry doctor` SHALL report it as a finding.

### US-6 — Doctor

As the maintainer, I want one command that verifies a repo's foundry state, so drift is
caught before it bites.

- AC-6.1 WHEN `foundry doctor` runs, THE SYSTEM SHALL run every check in the doctor
  check table:

  | Check | Passes when |
  |---|---|
  | config | `.foundry/config.toml` parses; pin matches the running CLI version |
  | manifest | every manifest hash matches its installed file |
  | adapters | each routed harness is in the manifest's harness set and its adapter is available (conformance is tested in this repo's suite, AC-2.2) |
  | hooks | `.githooks/` is the repo's `core.hooksPath` and pre-push runs the pinned gate |
  | board | `roadmap/ROADMAP.md` passes the board schema check |

- AC-6.2 WHEN any check fails, THE SYSTEM SHALL print one finding per failure with its
  fix and exit non-zero.

### US-7 — Materializer (bootstrap and update as code)

As the maintainer, I want bootstrap and update to be deterministic code, so materialized
files never depend on an LLM copying correctly.

- AC-7.1 WHEN `foundry bootstrap` runs, THE SYSTEM SHALL materialize templates (shipped inside
  the package) deterministically and idempotently — a re-run over a pristine install
  writes nothing — and stamp `.foundry/manifest.json` with name, version, and sha256 per
  file.
- AC-7.2 THE SYSTEM SHALL keep the interview a judgment step (headless or interactive
  harness call) whose answers feed the materializer as data; file writes are code.
- AC-7.3 WHEN `foundry update` runs, THE SYSTEM SHALL apply migrations as versioned code
  keyed by convention version; a customized file (hash mismatch) is flagged, never
  overwritten.

### US-8 — Eval matrix runner

As the maintainer, I want evals runnable headlessly across harness × model, so gate
discrimination is measured, not asserted.

- AC-8.1 WHEN `foundry eval --matrix <harness×model list>` runs, THE SYSTEM SHALL execute
  the repo's eval fixtures under each combination via the driver's headless path and
  report per-cell pass/fail and cost.
- AC-8.2 THE SYSTEM SHALL grade a generated gate by discrimination — a seeded defect must
  make it fail — never by green-ness alone.

### US-9 — PR-review runner

As the maintainer, I want `foundry review <pr>` to run the review stage headlessly
against a GitHub PR, so review conversations are durable and visible.

- AC-9.1 WHEN `foundry review <pr-number>` runs, THE SYSTEM SHALL check out the PR head
  in an isolated worktree, run the review stage (reviewer + refuter convergence) via the
  driver, and post each blocking or advisory finding as a PR review comment anchored to
  `file:line`.
- AC-9.2 THE SYSTEM SHALL never approve, merge, or dismiss reviews; posting comments is
  its only write.

### US-10 — Skill layer as stage rubrics

As the maintainer, I want each judgment stage's skill content rebuilt as a stage rubric
— intent, invariants, output contract — so stage prompts never instruct the model to do
the driver's work, and gates read declared output.

- AC-10.1 WHEN the driver compiles a judgment stage's prompt, THE SYSTEM SHALL compose
  it from the stage's rubric(s) and card context; a rubric SHALL carry no orchestration
  step (worktree, board, commit, push — driver vocabulary).
- AC-10.2 WHERE a judgment stage's gate reads harness output, THE SYSTEM SHALL evaluate
  it from the rubric's declared output contract (a last-line marker or JSON verdict),
  never from free text; command-shaped gates pass on exit status (design D1).
- AC-10.3 WHERE a v1 skill is pure orchestration (`code`, `handoff`), THE SYSTEM SHALL
  retire it in the wave whose driver mechanism replaces it (TR-3); advisory skills
  (`naming-standards`, `design-patterns`, `modular-structure`, `performance`, `debug`,
  `extract-skill`) SHALL stay interactively invocable in their current home and be
  composable into stage prompts.
- AC-10.4 WHEN the spec stage runs, THE SYSTEM SHALL require `design.md` to declare the
  feature's **public surface** (new or changed types, signatures, wire formats, config
  keys) and its **invariants** (properties that must always hold); a missing section is
  a spec-stage gate failure.
- AC-10.5 WHERE the spec stage cannot resolve an invariant or public-surface decision,
  THE SYSTEM SHALL emit it as `open_questions` in the stage's output contract; the
  driver SHALL surface each at the stage boundary per the autonomy level — supervised
  and guided ask the user, autonomous records it as a stated assumption in `design.md`
  and flags it in the run summary.

## Transition requirements

- TR-1 WHILE Waves 0–3 land, the v1 plugin skills and `check-fast.sh` SHALL keep working;
  v2 code SHALL NOT break the existing gate.
- TR-2 WHEN templates move into the CLI package (Wave 4), the self-host byte-identity
  check SHALL move with them in the same PR.
- TR-3 v1 mechanisms replaced by v2 (tmux spawn, convergence-hook scripts, prose
  update mechanics) SHALL be deleted in the wave that replaces them, not left parallel.

## Out of scope (v2)

- Harnesses beyond `claude-code` and `codex` (the adapter format makes them config).
- Rewriting the advisory skills' method content (US-10 reshapes homes and strips
  orchestration, not judgment); per-model skill compilation variants (deferred until
  routing data shows the need).
- MCP servers, marketplace polish, external telemetry, multi-repo orchestration.
- Rebuilding the harness-deliberation broker (it keeps working as-is; a driver transport
  is a later card).
- Windows support (macOS and Linux only).

## Non-functional

- NF-1 Python ≥ 3.11, uv-managed, src layout at the repo root (`pyproject.toml`,
  `src/foundry/`) so `uvx --from git+<repo-url>@<tag>` works with no packaging step.
- NF-2 Runtime dependencies: stdlib only (`argparse`, `tomllib`, `json`, `subprocess`);
  `pytest` as the sole dev dependency. GitHub access via the `gh` CLI, not an HTTP client.
- NF-3 No daemon, no database; all state is files under `.foundry/`.
- NF-4 Minimalism: every command earns its place; prefer deleting a v1 mechanism over
  keeping two ways to do one thing.
