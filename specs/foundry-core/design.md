# Foundry core — design

**Status:** Validating (2026-06-10) — tracked on the [board](../../docs/ROADMAP.md).
Companion: [requirements.md](requirements.md).

## Shape

One git repo, self-hosted with its own conventions, doubling as a plugin marketplace
with a single plugin:

```
foundry/
  .claude-plugin/marketplace.json
  plugins/foundry/
    .claude-plugin/plugin.json        # explicit version field (AC-2.3)
    skills/
      bootstrap/SKILL.md              # /foundry:bootstrap
      update/SKILL.md                 # /foundry:update
      code/SKILL.md                   # generalized lifecycle
    agents/
      spec-reviewer.md
    templates/                        # verbatim-copy files, version-marked
  evals/
    fixtures/                         # rust-cli/, python-service/, ts-monorepo/
    harness/                          # headless runner + graders + answer keys
  specs/  docs/  scripts/  features/  # foundry's own self-hosted setup
```

Install once at user scope (`claude plugin marketplace add bmransom/foundry`;
`/plugin install foundry@foundry`); skills and agents are then live in every repo.

**Portability principle.** Everything that defines the engineering system lands in
portable repo files (AGENTS.md, glossary, board, gates, features) that any agent or
human can follow. The plugin carries only Claude-native machinery: skill triggering,
the review agent, the bootstrap interview. Aligns with the AGENTS.md open standard;
degrades gracefully for non-Claude tools.

## The split

| Plugin (shared, auto-propagates) | Verbatim templates (version-marked) | Generated per-repo (stack-aware) |
|---|---|---|
| `code` lifecycle skill | `scripts/docs.py` + `test_docs.py` (DOC_GLOBS in a config block) | `AGENTS.md` + `CLAUDE.md` symlink |
| `spec-reviewer` agent | `docs/.vitepress/` config, `package.json`, `tsconfig.json` | `scripts/check-fast.sh` (real gate commands) |
| `bootstrap` + `update` skills | `scripts/board.sh`, `install-hooks.sh`, `worktree-retire.sh`, `.githooks/pre-push` | optional `scripts/verify.sh` (heavy gate + lock, only when an expensive validation exists) |
| Spec format definition (Wave/EARS) | `docs/{index,README}.md`, `ROADMAP.md`, `BACKLOG.md`, `validation.md`, `specs/README.md`, `features/README.md` | `features/` + BDD runner wiring + walking-skeleton Scenario |
| | `docs/glossary.md` stub (debt column; entity-model section empty) | CI workflow running `check-fast.sh` |
| | `.claude/rules/spec-conventions.md`, COE template | optional `scripts/vocab-lint`, isolation pattern (below) |

## Bootstrap flow

1. **Inspect** — detect languages, build tools, test frameworks, entrypoints, repo
   shape (service / library / CLI).
2. **Interview** — project description; 5–10 domain terms plus the wrong names that
   keep appearing (seeds the glossary and debt column); API surface?; existing gate
   commands; parallel agents on this machine?; vocabulary polarity (see below).
3. **Copy** verbatim templates, stamping version markers.
4. **Generate** the stack-aware column: BDD runner per stack (cucumber-rs /
   pytest-bdd / cucumber-js), one runner per production entrypoint the repo actually
   has; Contracts section when an API surface exists (zod+orpc / pydantic /
   serde+schemars: schema first, types derived, boundary validation); isolation per
   repo shape.
5. **Verify** — hooks installed, vitepress builds, walking-skeleton Scenario green,
   `check-fast.sh` passes end-to-end. The bootstrap grades its output through the
   gate it just created, and the eval harness independently guards against the
   vacuous-gate failure mode (§Evals).

### Isolation patterns (by interview)

| Repo shape | Pattern |
|---|---|
| Service/app, parallel agents | `scripts/agent-env.sh`: per-worktree `.env`, deterministic free ports; testcontainers wiring for integration tests |
| Resource-heavy single-host gate | machine-global mkdir-lock in `verify.sh`, stale-lock reclaim |
| Library / solo | `worktree-retire.sh` + explicit-paths staging rule only |

## Conventions carried (mechanisms, not content)

**Board.** Card schema `Work | Status | Spec | Depends on`; claim-by-owner; status
taxonomy; epic order = priority; "Done requires a recorded gate PASS"; bidirectional
spec↔board pointers with the board-wins rule; `BACKLOG.md` keeps the idea pool off
the board. `board.sh` ships unchanged.

**Glossary, six-layer reinforcement.** The same rule meets the agent at every
altitude: (1) AGENTS.md Always-line ("the glossary is the contract"); (2) glossary
preamble authority claim ("this file wins; code is debt"); (3) the **debt column**
mapping the names a model reaches for to the canonical ones; (4) ROADMAP Standing
rules naming stub restating the top rules where work is planned; (5) path-scoped
`spec-conventions.md` rule on `specs/**` mandating glossary terms and the
spec-reviewer dispatch; (6) gates — spec-reviewer editorially, `vocab-lint`
mechanically (grep driven by the debt column). **Polarity is per-repo**: an engine
repo excludes consumer vocabulary (octant's case); a product repo embraces domain
terms. The interview asks; the mechanism is identical.

**Lifecycle.** Frame routes by work size (bug fix and refactor skip the spec —
the ceremony-scaling answer to the known SDD failure mode); Spec gates on approval +
spec-reviewer; Plan claims the card; Build is feature-file-first then TDD; Verify
requires the pasted PASS; Docs requires `docs.py check` clean and indexed; Finish
moves the card, Done needs the recorded gate PASS. All commands and paths read from
the consumer repo's AGENTS.md.

**Gates, two triggers.** The same `check-fast.sh` runs from `.githooks/pre-push`
(fast feedback, bypassable) and CI (non-bypassable backstop). `verify.sh` exists
only where an expensive validation does.

**COE.** Template ships in every bootstrap: what happened, root cause, blast
radius, the mechanical fix, the eval case spawned. Closure rule: prose alone never
closes a COE. Promotion rule: root cause in shared machinery → the COE moves to
foundry and adds a fixture/answer-key case. Octant's production-path COE is the
worked example: it becomes the seeded defect proving the production-path lint
discriminates.

## Update mechanism

Skills/agents: plugin install propagates. Templates: `/foundry:update` diffs each
version-marked file against the current template; refreshes unmodified files;
flags customized ones with the diff instead of overwriting. Explicit `version` in
`plugin.json`; a bump requires a green Layer-3 run (AC-2.3), so versions mean
something.

## Evals

| Layer | Trigger | Grader |
|---|---|---|
| 1 unit + self-host | every commit | template tests; foundry's own gate; byte-identity of foundry's verbatim copies vs `templates/` |
| 2 bootstrap e2e | every PR touching templates/bootstrap | harness bootstraps each fixture headless (`claude -p --plugin-dir`), then: harness-owned invariants + **gate discrimination** — every seeded defect on the fixture's defect branch must fail the generated gate; clean branch must pass |
| 3 behavioral | version bump | spec-reviewer precision/recall vs seeded answer keys, N runs with variance; lifecycle tasks graded by mechanically checkable artifacts (Scenario commit precedes implementation; PASS pasted; card claimed; no `git add -A`); LLM-judge only where mechanics can't reach, rubric + majority vote |
| 4 COE accretion | each real failure | the promoted COE's fixture becomes a permanent Layer-2/3 case |

**Independence rule (AC-5.4).** A generated gate is never graded by its own
green-ness: the gate was produced by the system under test, so a vacuous gate would
self-certify. Discrimination against seeded defects is the grade.

**Known limits.** Layer 3 at affordable N detects large regressions, not subtle
ones — report variance, treat as a smoke alarm. Ecosystem drift (Claude Code and
model behavior changing under foundry) is not catchable by commit-triggered evals;
mitigate by re-running Layer 3 on Claude Code releases.

## Self-hosting

Foundry develops under its own conventions from day one (this spec, the board, the
glossary are the start). Chicken-and-egg resolved by hand-writing foundry's own
setup first, then replacing each piece with its extracted template; the Layer-1
byte-identity check makes convergence mechanical. End state: foundry's own setup is
reproducible by its own bootstrap.

## Octant-ism audit

Carried mechanisms with octant content removed:

| Octant-ism | Resolution |
|---|---|
| Entity model hardcoded in spec-conventions + spec-reviewer | both read "the entity model defined in the repo's glossary" |
| Domain-neutrality as the vocabulary rule | polarity is an interview question; the lint mechanism is shared |
| Two-tier gate assumed | `verify.sh` + lock conditional on an expensive validation existing |
| Dual-entrypoint BDD | one runner per actual production entrypoint |
| `solve.feature`/`cli_only.feature` names | pattern documented in `features/README.md` (outcome vs process contracts), names per-repo |
| ROADMAP standing rules content | template ships the naming stub only |
| Benchmarking rule detail | AGENTS.md skeleton carries two principles: production-entrypoint-only, and grader independence; detail stays in octant |
| `docs.py` DOC_GLOBS | config block at top of template |
| Crate map, Netlib, TIMEOUT_ALLOW, lp-result-triage | excluded |

**Meta-rule:** foundry ships mechanisms and patterns; repos supply the content.

## Decisions log

Polyglot targets · shared core as a plugin (not one-shot copy, not copier template)
· hybrid bootstrap (verbatim + generated; not fully-LLM, not fully-templated) ·
plugin over a standalone scaffolding agent (distribution + versioning + propagation;
agents are used *inside* the design where context isolation pays: spec-reviewer) ·
CI mirroring and explicit versioning added after best-practice review · COE and
self-hosting adopted 2026-06-10.
