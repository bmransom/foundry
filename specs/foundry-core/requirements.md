# Foundry core — requirements

**Status:** Validating (2026-06-10) — tracked on the [board](../../docs/ROADMAP.md).

## Overview

Foundry is a Claude Code plugin that bootstraps the octant-style AI-assisted
engineering setup into any repo, polyglot: spec-driven development (Wave/EARS),
executable Gherkin features, a vitepress doc site with frontmatter-driven discovery,
a tracked kanban board with spec pointers, a glossary-as-contract, two-trigger
verification gates (pre-push + CI), contract-first APIs, agent-isolation patterns,
and COE-driven eval accretion. Generic parts live in the versioned plugin and
propagate on update; per-repo parts are installed by a hybrid bootstrap (verbatim
templates + stack-aware generation).

## User stories

**US-1 Bootstrap.** As a developer starting a repo, I run `/foundry:bootstrap`,
answer a short interview, and get the full setup installed, wired to my stack, and
proven working — so a new project starts with the discipline octant evolved.

- AC-1.1 WHEN bootstrap completes, THE SYSTEM SHALL have produced: `AGENTS.md` +
  `CLAUDE.md` symlink, `docs/` (vitepress + ROADMAP + BACKLOG + glossary + index +
  validation skeleton + COE template), `specs/`
  with format README, `features/` with a walking-skeleton Scenario wired to a
  stack-appropriate BDD runner, `scripts/` (docs.py, board.sh, check-fast.sh,
  install-hooks.sh, worktree-retire.sh), `.githooks/pre-push`, and a CI workflow
  running the same quick gate.
- AC-1.2 WHEN bootstrap finishes, THE SYSTEM SHALL have verified its own output:
  hooks installed, vitepress builds, the walking-skeleton Scenario passes, and the
  quick gate passes — a recorded PASS, not a claim.
- AC-1.3 WHEN the target repo is Rust, Python, or TypeScript (or a mix), THE SYSTEM
  SHALL wire the BDD runner (cucumber-rs / pytest-bdd / cucumber-js) and gate
  commands to the detected stack.
- AC-1.4 WHEN the repo has an API surface (per the interview), THE SYSTEM SHALL add
  a Contracts section to AGENTS.md (schema first, types derived, boundary
  validation) using the stack mapping (zod+orpc / pydantic / serde+schemars).
- AC-1.5 WHEN the interview indicates parallel agents on one machine, THE SYSTEM
  SHALL install the matching isolation pattern (per-worktree env + ports,
  testcontainers, or a machine-global gate lock).
- AC-1.6 WHERE a verbatim template is installed, THE SYSTEM SHALL stamp it with a
  version marker (`foundry-template: <name> v<N>`).
- AC-1.7 WHEN the target repo is an application or service, THE SYSTEM SHALL write
  a Logging section in AGENTS.md (structured wide events — one canonical event per
  unit of work; glossary vocabulary for field names; trace/span correlation IDs)
  and SHALL wire the stack-standard library (`tracing` / `structlog` / `pino`)
  with one working example event.

**US-2 Update propagation.** As the maintainer, when I improve foundry, consumer
repos receive the improvement — skills and agents automatically via the plugin,
templates via an explicit re-sync.

- AC-2.1 WHEN the plugin version is bumped and installed, THE SYSTEM SHALL serve
  the new skills/agents in every consumer repo with no per-repo action.
- AC-2.2 WHEN `/foundry:update` runs in a consumer repo, THE SYSTEM SHALL diff each
  version-marked file against the plugin's current template, refresh unmodified
  files, and flag locally-customized ones instead of overwriting.
- AC-2.3 THE SYSTEM SHALL use an explicit `version` field in `plugin.json`; a
  version bump SHALL ship only with a green Layer-3 eval run.

**US-3 Lifecycle.** As an agent working in a consumer repo, the generalized `code`
skill holds me to the staged lifecycle with mechanical gates.

- AC-3.1 THE skill SHALL enforce Frame → Spec → Plan → Build → Verify → Docs →
  Finish with the gate prohibitions, reading repo-specific commands and paths from
  the consumer repo's AGENTS.md (never hardcoding foundry or octant values).
- AC-3.2 WHEN work is framed as a bug fix or refactor, THE skill SHALL route around
  the full spec path (the ceremony-scaling rule).
- AC-3.3 WHEN new observable behavior is built, THE skill SHALL require its
  Scenario in `features/` before its implementation.

**US-4 Spec review.** As a spec author, the spec-reviewer agent checks naming and
prose against my repo's contract files.

- AC-4.1 THE agent SHALL read the consumer repo's `docs/glossary.md` (including its
  entity model, if any) and AGENTS.md writing style at review time; criteria come
  from files, not the agent's priors.
- AC-4.2 THE agent SHALL flag debt-column terms, entity-model misfits, and prose
  violations; it SHALL be read-only.

**US-5 Evals.** As the maintainer, I can tell whether a foundry change is an
improvement before shipping it.

- AC-5.1 Layer 1: template unit tests and foundry's self-hosted gate SHALL run on
  every commit; verbatim-template copies in foundry's own tree SHALL be
  byte-identical to `plugins/foundry/templates/` (modulo marker).
- AC-5.2 Layer 2: WHEN a PR changes templates or the bootstrap skill, THE eval
  harness SHALL bootstrap each fixture headless and grade by harness-owned
  invariants plus gate discrimination: every seeded defect SHALL make the generated
  gate fail, and the clean branch SHALL pass.
- AC-5.3 Layer 3: WHEN the plugin version is bumped, THE spec-reviewer suite SHALL
  report precision/recall against seeded answer keys across N runs, and lifecycle
  tasks SHALL be graded by mechanically checkable artifacts (Scenario precedes
  implementation; PASS pasted; no `git add -A`).
- AC-5.4 THE SYSTEM SHALL never grade a generated gate by its own green-ness alone.

**US-6 COE accretion.** As the maintainer, real failures permanently strengthen the
setup.

- AC-6.1 Bootstrap SHALL install the COE convention (template + doc kind) in every
  consumer repo.
- AC-6.2 A COE SHALL be closed only by a mechanical change: a gate, lint, rule, or
  eval fixture.
- AC-6.3 WHEN a COE's root cause is shared machinery (template or skill), THE COE
  SHALL be promoted to foundry and SHALL spawn an eval case there.

## Out of scope (v1)

Octant retrofit (own card, own spec); non-Claude agent runtimes beyond what
AGENTS.md portability already gives; team/multi-user marketplace governance;
Layer-4 telemetry beyond COE promotion.
