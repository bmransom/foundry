> **Status:** Ready (2026-06-16) — tracked on the [board](../../ROADMAP.md).

# Requirements — harness-agnostic foundry

## Overview

Foundry is a Claude Code plugin: its own skills and `spec-reviewer` run only under
Claude Code, and `bootstrap` emits a setup with a few Claude-only assumptions. But
the two layers that carry an AI-engineering setup are now cross-harness standards —
`AGENTS.md` (Linux Foundation) for instructions and Agent Skills (`SKILL.md`,
agentskills.io) for procedures — adopted by Codex, Gemini, Cursor, and ~40 tools.
Foundry already emits `AGENTS.md`, so a bootstrapped repo is already *nearly*
harness-neutral today. The gap is the other direction: foundry itself cannot run
anywhere but Claude Code.

This feature makes foundry harness-agnostic on both sides, across three axes:

- **Axis A — foundry runs under Codex.** Its skills (`bootstrap`, `code`, `update`)
  and `spec-reviewer` run under Codex as well as Claude Code. The substantial work —
  these live plugin-side.
- **Axis B — bootstrap emits for the selected harness(es).** The interview chooses
  the targets; each reads the setup natively. A thin completion — the emitted repo is
  already mostly neutral.
- **Axis C — existing repos retrofit.** A convention-version-3 migration reuses the
  `migration-aware-update` machinery.

A **harness** is the new canonical term for an AI coding tool that runs foundry's
skills and consumes a bootstrapped repo (Claude Code, Codex, …). Its prior art is
**agent-harness engineering** (2026): the runtime that wraps an LLM — the model
proposes, the harness validates and executes — where Claude Code, Codex, and Cursor
are each an *agentic harness* and skills are one of its layers. Foundry prefers
*harness* over the standards' *coding agent* to avoid colliding with its own *agent*
(the executing AI) and *subagent* (a dispatched worker). Foundry's *mechanisms*
(specs, gates, knowledge, board) are already harness-neutral; this feature touches
only the thin coupling at the edges — invocation form, install location, the single
subagent format, the `CLAUDE.md` shim, and the rules path — not the method.

## User stories

### Story 1 — run foundry from Codex

- **As a** developer who works in Codex
- **I want** to install foundry and run `bootstrap`, `code`, `update`, and the
  `spec-reviewer`
- **So that** I get the same engineering setup without switching to Claude Code

### Story 2 — bootstrap a repo for the harness(es) the team uses

- **As a** developer bootstrapping a repo
- **I want** to declare which harness(es) the team uses and have foundry emit a setup
  each one reads natively
- **So that** no teammate is locked to one tool and the conventions stay single-source

### Story 3 — retrofit a repo bootstrapped before this feature

- **As a** maintainer of a repo bootstrapped Claude-only
- **I want** `/foundry:update` to bring it to the harness-agnostic layout and add a
  harness without hand-editing
- **So that** the repo becomes portable in one command, safely and reversibly

### Story 4 — add the next harness as a mapping, not a rewrite

- **As a** foundry maintainer
- **I want** each supported harness expressed as one mapping — install location,
  invocation form, instruction file, subagent format
- **So that** supporting the harness after Codex is a table row, not a redesign

## Acceptance criteria

### Vocabulary

- **AC-1.1** WHEN the glossary defines the term, THE SYSTEM SHALL record **harness**
  as the canonical name for an AI coding tool that runs foundry skills and consumes a
  bootstrapped repo, citing its prior art — *agent-harness engineering* (2026), where
  a coding agent such as Claude Code or Codex is the *harness* that wraps the LLM and
  loads skills — and recording why it is preferred over the standards' *coding agent*:
  to avoid colliding with foundry's *agent* (the executing AI) and *subagent*. THE
  SYSTEM SHALL record the debt terms it replaces — *agent* in its tool sense, *host*
  (as in "the host's question tool") — and SHALL leave *agent* (the executing AI) and
  *subagent* (a dispatched worker such as `spec-reviewer`) intact.
- **AC-1.2** WHEN the manifest relocates (AC-4.7), THE SYSTEM SHALL update both
  glossary entries that name the manifest path — *Manifest* and *Convention version* —
  to `.foundry/manifest.json`, and record the added `harnesses` field, keeping the
  vocabulary contract current.

### Foundry runs under Codex (Axis A)

- **AC-2.1** WHERE foundry is installed for Codex, THE SYSTEM SHALL expose
  `bootstrap`, `code`, and `update` as Codex skills the caller can invoke, executing
  the same `SKILL.md` bodies as under Claude Code.
- **AC-2.2** THE SYSTEM SHALL keep every shipped `SKILL.md` frontmatter to the Agent
  Skills required set (`name`, `description`), so each skill loads unmodified on any
  Agent-Skills harness. (True today; this guards it.)
- **AC-2.3** WHERE a skill body names its own invocation or another foundry skill,
  THE SYSTEM SHALL NOT hardcode a Claude-Code-only command form (`/foundry:bootstrap`);
  it SHALL use a reference that resolves under each supported harness.
- **AC-2.4** WHEN a skill resolves its bundled templates or references, THE SYSTEM
  SHALL locate them relative to the skill's own install directory under each harness,
  never by a path that assumes the Claude Code plugin layout.
- **AC-2.5** WHERE the `code` skill delegates spec review, THE SYSTEM SHALL dispatch
  `spec-reviewer` through the running harness's subagent mechanism, or degrade to an
  inline review where the harness has none — never skip the review.
- **AC-2.6** THE SYSTEM SHALL keep `spec-reviewer` a single `agents/spec-reviewer.md`:
  Claude Code and Codex read the same markdown-and-frontmatter agent format, so one file
  serves both — no twin, no drift. Its frontmatter SHALL stay to the subset both
  harnesses honor, and it SHALL remain read-only.
- **AC-2.7** THE SYSTEM SHALL be installable under Codex via harness-appropriate
  manifests — a neutral `.agents/plugins/marketplace.json` and a
  `plugins/foundry/.codex-plugin/plugin.json` — so Codex never reads a `.claude-plugin/`-named
  path (`codex plugin marketplace add` discovers `foundry@foundry`), delivering
  AC-2.1–AC-2.6. The install path SHALL be documented.

### Harness selection at bootstrap (Axis B)

- **AC-3.1** WHEN the bootstrap interview runs, THE SYSTEM SHALL ask which harness(es)
  the repo targets — at least Claude Code and Codex, multi-select — and record the
  answer; WHERE the harness offers no question tool, it SHALL accept a canned answer.
- **AC-3.2** WHEN bootstrap writes the instruction contract, THE SYSTEM SHALL make
  `AGENTS.md` the single source for every selected harness; WHERE Claude Code is
  selected, it SHALL add `CLAUDE.md` as a pointer to `AGENTS.md`; WHERE Claude Code is
  not selected, it SHALL NOT emit `CLAUDE.md`.
- **AC-3.3** WHEN bootstrap emits convention files that a harness would otherwise read
  from a harness-specific path (the rules seeds), THE SYSTEM SHALL place them in a
  harness-neutral location referenced from `AGENTS.md`, not a `.claude/`-only path.
- **AC-3.4** WHEN bootstrap writes the manifest at `.foundry/manifest.json`, THE
  SYSTEM SHALL record the selected harness set, so update and migration know what to
  maintain.
- **AC-3.5** WHEN bootstrap completes, THE SYSTEM SHALL verify each selected harness
  can read the setup — the instruction file resolves for each, and a not-selected
  harness's shim is absent.

### Retrofit existing repos (Axis C, convention version 3)

- **AC-4.1** THE registry SHALL gain a migration keyed to convention version 3
  (harness-agnostic) that brings a convention-2 repo to the harness-agnostic layout.
- **AC-4.2** WHEN the convention-3 migration runs, THE SYSTEM SHALL move any
  `.claude/`-only convention path (the rules seeds) to the harness-neutral location
  and rewrite references to it, preserving git history (rename, not delete-plus-create).
- **AC-4.3** WHEN the convention-3 migration runs, THE SYSTEM SHALL record the repo's
  current harness set in the manifest and stamp `conventionVersion` 3.
- **AC-4.4** WHEN the caller asks update to add a harness to a consumer repo, THE
  SYSTEM SHALL emit only that harness's reads — a `CLAUDE.md` pointer for Claude Code,
  nothing extra for a harness that reads `AGENTS.md` natively — and add it to the
  manifest harness set, idempotently.
- **AC-4.5** THE convention-3 migration SHALL obey the `migration-aware-update` safety
  rules — clean-tree refusal, dry-run report, dedicated branch, no-regression gate,
  idempotent detector — and SHALL make no change on a repo already at convention 3.
- **AC-4.6** WHEN `/foundry:update` runs on a repo whose manifest records a harness
  set, THE SYSTEM SHALL maintain that set without re-asking the interview's harness
  question; it SHALL prompt only when the caller asks to add or remove a harness
  (AC-4.4). The recorded set is the source of truth for which harnesses to maintain.
- **AC-4.7** WHEN the convention-3 migration runs, THE SYSTEM SHALL move
  `.foundry-manifest.json` to `.foundry/manifest.json`, preserving git history, and
  rewrite any reference to the old path. The migration's detector SHALL treat a
  top-level `.foundry-manifest.json` as a convention-<3 marker; `/foundry:update`
  SHALL read the manifest from `.foundry/manifest.json`, falling back to the legacy
  top-level path for an unmigrated repo.

### Verification (independent oracle)

- **AC-5.1** THE grading SHALL be harness-owned — fixtures and scans that share no
  code with foundry's skills; the skills' own checks SHALL never grade themselves.
- **AC-5.2** AN eval SHALL prove foundry's skills run headless under Codex — a
  `codex`-exec analog to the existing `claude -p` evals — bootstrapping a fixture green
  end to end.
- **AC-5.3** AN eval SHALL prove a bootstrapped multi-harness repo is readable by each
  selected harness and carries no shim for a harness it did not select.
- **AC-5.4** AN eval SHALL prove the convention-3 migration retrofits a convention-2
  fixture — neutral rules location, manifest harness set, `conventionVersion` 3,
  idempotency, gate no-regression — graded by a harness-owned scan, with a seeded
  incomplete migration the scan must fail.
- **AC-5.5** AN eval SHALL prove `spec-reviewer` parity across harnesses — the shared
  source yields the same findings on a fixture under Claude Code and Codex.
- **AC-5.6** THE self-host SHALL converge: foundry's own repo SHALL pass the
  multi-harness readability invariants (AC-5.3) for its declared harnesses, and a
  foundry skill SHALL run under `codex exec` against foundry's own repo (the dogfood
  acceptance) — staged after the Codex path is green under Claude Code.

## Out of scope

- Harnesses beyond Claude Code and Codex. The design SHALL make adding one a mapping;
  only the two ship now.
- MCP servers — foundry ships none; no per-harness MCP config to emit.
- Codex hooks wiring — foundry's gate is a git `pre-push` hook, already harness-neutral.
- Reinventing `AGENTS.md` or the Agent Skills standard — foundry consumes them.
- A general harness-abstraction framework — only the mappings the two harnesses need.
- Divergent per-harness *content* — the contract stays single-source in `AGENTS.md`;
  harness files are thin shims or symlinks.
- Changing foundry's engineering method (specs, gates, knowledge, board) — neutral
  already.
- Rolling a migration back — recovery is `git revert`, per `migration-aware-update`.

## Dependencies

- **`AGENTS.md`** (Linux Foundation) and **Agent Skills** (agentskills.io) — the
  cross-harness standards that carry portability; foundry's `SKILL.md` files are
  already compliant (`name` + `description` only).
- **`migration-aware-update`** (Epic 3) — the convention-version registry, ordered
  chain, and migration safety machinery the convention-3 entry reuses.
- **`foundry-core`** — the plugin, skill, agent, and manifest architecture being
  generalized across harnesses.
- **The manifest mechanism** (`bootstrap` SKILL.md §3) — gains a harness-set field
  beside `conventionVersion`.
- **Codex conventions** — skills in `.agents/skills/` invoked with `$`; subagents as
  `.codex/agents/*.toml` (`developer_instructions`, `sandbox_mode`); plugins as a
  `plugin.json` with a `components` block. The target formats for AC-2.

## Verification plan (detailed in design)

Fixtures plus harness-owned grading, mirroring the existing eval layers. A
`codex`-exec eval runs foundry's skills headless and asserts a green bootstrap
(AC-5.2). A bootstrap eval asserts per-harness readability and shim absence (AC-5.3).
A convention-3 migration eval, built on the `migration-eval` pattern, asserts the
retrofit and fails a seeded incomplete migration through a harness-owned scan
(AC-5.4). A reviewer-parity eval runs the shared `spec-reviewer` source under both
harnesses against the reviewer fixture and compares findings (AC-5.5). The design
carries the fixture matrix and the harness mapping table.
