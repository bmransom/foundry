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
    templates/{verbatim,seeds}/       # byte-checked tooling / repo-owned starting points
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

**Template classes.** `templates/verbatim/` holds tooling that stays byte-identical
in every repo — gates, hooks, scripts, vitepress config; the self-host byte-identity
gate enforces it. `templates/seeds/` holds content starting points — board, glossary,
doc stubs, rules, the COE template — copied once at bootstrap, then owned by the
repo; never byte-checked, divergence is the point. Seeds carry `foundry-seed:`
markers so `/foundry:update` can announce a newer seed without overwriting. Any
per-repo variation a verbatim tool needs lives in a seed config file (docs.py reads
`docs/docs-config.json`; the vitepress config reads `docs/.vitepress/site.json`),
keeping the tool itself byte-stable.

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
repo excludes consumer vocabulary (the reference repo's case); a product repo embraces domain
terms. The interview asks; the mechanism is identical.

**Naming with prior art.** The glossary layers enforce consistency with chosen
terms; this convention governs how a term gets chosen. Before coining any canonical
name — a glossary term, a public type or field, a config knob — search the prior
art: the domain's literature, the stack's naming conventions (PEP 8, the Rust API
Guidelines, ecosystem idiom), and what leading comparable tools call the same
concept (web search when local knowledge runs out). Prefer the established name; an
invented one records why prior art doesn't fit. Enforced at four points: the
glossary preamble states the rule; the `spec-conventions` rule mandates the search
at the coining moment; `spec-reviewer` flags new terms that name no prior art and
no reason; the lifecycle Spec stage carries the step. Foundry's own glossary
complies: COE is AWS vocabulary, wide event is Stripe/Honeycomb's, fixture is
xUnit's, seeded defect is mutation testing's.

**Context-economy prose.** Skills, agents, rules, AGENTS.md, and doc templates load
into context windows; every needless word costs tokens in every session that loads
it. The writing standard is Strunk & White — above all: omit needless words, use
the active voice, make definite assertions. Plugin-resident prose is held to it
hardest: when Wave 3 lands skills, `check-fast.sh` gains a context-budget lint
(flag a SKILL.md body, agent, or rule exceeding its size budget — budgets set in
Wave 3 when real files calibrate them). `spec-reviewer`'s prose scope extends
beyond specs to skill/agent/rule changes.

**Lifecycle.** Frame routes by work size (bug fix and refactor skip the spec —
the ceremony-scaling answer to the known SDD failure mode); Spec gates on approval +
spec-reviewer; Plan claims the card; Build is feature-file-first then TDD; Verify
requires the pasted PASS; Docs requires `docs.py check` clean and indexed; Finish
moves the card, Done needs the recorded gate PASS. All commands and paths read from
the consumer repo's AGENTS.md.

**Gates, two triggers.** The same `check-fast.sh` runs from `.githooks/pre-push`
(fast feedback, bypassable) and CI (non-bypassable backstop). `verify.sh` exists
only where an expensive validation does.

**Structured logging.** Application and service repos get a Logging section in
AGENTS.md: structured key-value events, never prose interpolation; one **wide
event** (canonical log line) per unit of work carrying identity, release metadata,
execution cost, and decision inputs; trace/span correlation IDs on every record
(OpenTelemetry semantic conventions where OTel is in play); field names come from
the repo glossary — the log schema is the glossary on the wire. Stack mapping:
`tracing` + JSON subscriber (Rust), `structlog` (Python), `pino` (TS/Node). The
interview names the unit of work (request, job, solve) so the canonical event has a
name from day one. The reference repo's NDJSON `Trace` is the worked example of the pattern.
Applied to foundry itself at its native scale: gates emit stable one-line
`key: value` verdicts (`check-fast: PASS`, `byte-identity: DRIFT <path>`), and the
eval harness (Wave 6) emits one NDJSON wide event per eval case (fixture, seeded
defect, verdict, duration, tokens).

**COE.** Template ships in every bootstrap: what happened, root cause, blast
radius, the mechanical fix, the eval case spawned. Closure rule: prose alone never
closes a COE. Promotion rule: root cause in shared machinery → the COE moves to
foundry and adds a fixture/answer-key case. The reference repo's production-path COE is the
worked example: it becomes the seeded defect proving the production-path lint
discriminates.

## Tooling decisions

**Repo scripts over agent tools.** `docs.py`, `board.sh`, and the gates stay plain
CLI scripts shipped as templates — not MCP tools, not plugin `bin/` executables.
Rationale: the portability principle (any agent, humans, and CI can run them; an
MCP tool is Claude-session-only), discovery is solved by AGENTS.md naming the
command, and a CLI has no extra process or config to fail. Plugin `bin/` was
considered and rejected: it would make consumer repos depend on the plugin being
installed, breaking self-containedness for CI and non-Claude users.

**Progressive disclosure has three levels; tooling covers the first two, grep the
third.**

| Level | Question | Mechanism |
|---|---|---|
| 1 — index | "what docs exist?" | `docs.py list` — kind + title + frontmatter description |
| 2 — outline | "what's in this 30 KB doc?" | `docs.py outline <doc>` — heading tree; `docs.py section <doc> <heading>` prints one section |
| 3 — retrieval | "where is X discussed?" | grep + targeted Read — already optimal, no tooling |

Level 2 (`outline`/`section`) is new in the Wave 2 template: it lets an agent pull
one section of a large reference doc instead of the whole file, mirroring the
manual → table-of-contents → chapter structure skills use. Level 3 stays grep:
a search index would be machinery without a failure it prevents.

## Update mechanism

Skills/agents: plugin install propagates. Templates: `/foundry:update` compares
each verbatim file against the plugin's current template — but "locally
customized" vs "older pristine version" is undecidable from content alone, so
bootstrap writes `.foundry-manifest.json`: the plugin version plus, per verbatim
file, its template name, version, and the sha256 of the installed content. Update
hash-checks each file: hash matches the manifest → pristine → refresh to the new
template and re-record; differs → customized → flag with the diff, never
overwrite. Seeds carry versions in their `foundry-seed:` markers; update announces
a newer seed and never touches the repo's copy. Pre-manifest repos get legacy
mode: files identical-modulo-marker to the current template are recorded pristine;
anything else is flagged for human review — no guessing. Explicit `version` in
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

## Reference-repo audit

Carried mechanisms with reference-repo content removed:

| Reference-repo idiom | Resolution |
|---|---|
| Entity model hardcoded in spec-conventions + spec-reviewer | both read "the entity model defined in the repo's glossary" |
| Domain-neutrality as the vocabulary rule | polarity is an interview question; the lint mechanism is shared |
| Two-tier gate assumed | `verify.sh` + lock conditional on an expensive validation existing |
| Dual-entrypoint BDD | one runner per actual production entrypoint |
| `solve.feature`/`cli_only.feature` names | pattern documented in `features/README.md` (outcome vs process contracts), names per-repo |
| ROADMAP standing rules content | template ships the naming stub only |
| Benchmarking rule detail | AGENTS.md skeleton carries two principles: production-entrypoint-only, and grader independence; detail stays in the reference repo |
| `docs.py` DOC_GLOBS | config block at top of template |
| Project-specific structure, datasets, tuning constants, domain skills | excluded |

**Meta-rule:** foundry ships mechanisms and patterns; repos supply the content.

## Decisions log

Polyglot targets · shared core as a plugin (not one-shot copy, not copier template)
· hybrid bootstrap (verbatim + generated; not fully-LLM, not fully-templated) ·
plugin over a standalone scaffolding agent (distribution + versioning + propagation;
agents are used *inside* the design where context isolation pays: spec-reviewer) ·
CI mirroring and explicit versioning added after best-practice review · COE and
self-hosting adopted 2026-06-10 · structured logging (wide events + OTel correlation
+ glossary field names) and the script-over-MCP tooling decision with `docs.py
outline`/`section` added 2026-06-10 · naming-with-prior-art and Strunk & White
context-economy prose adopted 2026-06-10.
