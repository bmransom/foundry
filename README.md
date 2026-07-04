# Foundry

[![CI](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml/badge.svg)](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml)
[![Release](https://img.shields.io/github/v/release/bmransom/foundry)](https://github.com/bmransom/foundry/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code and Codex plugin that installs a spec-driven engineering setup into any
repo: requirements-to-tasks specs, executable acceptance tests, a verification gate on
every push, a glossary-as-contract, and an OKF knowledge base. It wires the setup to your
stack and proves it green before the first commit. Foundry ships the mechanisms; your repo
supplies the content.

## Contents

- [Why](#why)
- [What foundry installs](#what-foundry-installs)
- [Two ways to work](#two-ways-to-work)
- [The plugin](#the-plugin)
- [Setup](#setup)
- [Quickstart](#quickstart)
- [Development](#development)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## Why

Discipline arrives late: specs after the code, tests after the bug, a gate after the
outage. Foundry installs it on day one, wired to your stack, so an agent or a human works
against real gates from the first commit. A reference repo proves the mechanisms; a
versioned plugin ships them.

## What foundry installs

`foundry bootstrap` detects your stack and installs a setup your repo then owns:

| Capability | Where |
|---|---|
| Spec-driven workflow: requirements → design → tasks, in EARS | `roadmap/specs/` |
| Executable Gherkin features through a real entrypoint, no mocks | `features/` |
| OKF knowledge base and its navigation tool | `knowledge/` |
| Glossary-as-contract: the vocabulary, entity model, and bounded contexts the agent must use | `knowledge/glossary.md` |
| Tracked board: the single source of truth for status | `roadmap/ROADMAP.md` |
| Verification gate — board, prose, knowledge, and your tests — on every push and in CI | `.foundry/bin/foundry gate` |
| Conventions, gates, and boundaries (with a `CLAUDE.md` symlink for Claude Code) | `AGENTS.md` |
| Vitepress doc site over the knowledge base | `knowledge/.vitepress/` |

The knowledge base follows the
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf):
plain markdown concepts with `type` frontmatter, a generated listing, and a change log. It
stays portable, not locked to the doc site.

## Two ways to work

Foundry runs a board card through one lifecycle — spec → plan → build → verify → knowledge
→ review → finish — two ways, graded by one set of rubrics:

- **The driver** runs it headlessly. `.foundry/bin/foundry run <card>` walks the stages
  with gates enforced in code, retries bounded, and every step recorded in a run ledger.
  Use it for unattended and CI work.
- **The skills** run it in your session. `/foundry:code` and its siblings walk the same
  stages, supervised, sharing your context — the driver's interactive twin. Use them to
  pair on a card.

A repo-local `.foundry/bin/foundry` shim resolves the pinned CLI from
`.foundry/config.toml`, so the gate, the driver, and CI run one version. You bump the pin
in one place.

## The plugin

Installed once at user scope, foundry runs in every repo. It ships the skills; bootstrap
installs the pinned CLI the gate and driver run through the shim.

**CLI** — `.foundry/bin/foundry <command>`:

| Command | What it does |
|---|---|
| `bootstrap` | Installs the setup into the current repo: inspect → interview → copy → generate → verify |
| `update` | Re-syncs installed templates on a version bump and crosses convention breaks; never touches your content |
| `run` | Drives a card through the lifecycle headlessly, recording a run ledger |
| `gate` | Runs the verification gate — board, prose, knowledge, and your tests |
| `review` | Reviews a GitHub PR against its spec, adversarially verified; posts anchored comments, never approves |
| `rubric` | Prints the stage map or one stage's rubric — the judgment the skills fetch |

**Skills** — invoked by name (`/foundry:<name>` in Claude Code):

| Skill | What it does |
|---|---|
| `code` | Drives a card through the lifecycle in your session — the driver's supervised twin |
| `spec-review` | Reviews a spec or context-resident prose against the glossary and writing style, in fresh context |
| `code-review` | Grades a diff against its spec — completeness, docs sync, defaults, test discrimination |
| `knowledge` | Maintains the OKF base — home selection, the four types, provenance, coherence |
| `handoff` | Captures verified state and starts a same-harness successor session |
| `performance` | Treats performance work as a lifecycle concern: baseline → benchmark → profile → attribute |
| `naming-standards` | Reviews glossary, API, file, metric, and config names before they become contracts |
| `design-patterns` | Chooses Strategy, Adapter, Observer, Factory, Builder, Facade, Decorator, Command, and State when they earn their complexity |
| `modular-structure` | Reviews directory layout, module boundaries, dependency direction, and public APIs |
| `debug` | Drives `lldb` to localize a fault in native code — breakpoints, stepping, frame and variable inspection |
| `extract-skill` | Distills a reusable workflow from a session into a user, repo, or plugin skill |
| `harness-deliberation` | Mediates a Codex + Claude design session with a recorded decision |

`spec-review`, `code-review`, and `knowledge` grade against the same rubrics the driver
compiles, so the interactive and headless paths never diverge.

## Setup

**Requirements:** [Claude Code](https://docs.claude.com/en/docs/claude-code) or
[Codex](https://developers.openai.com/codex), and a git repository. Bootstrap wires Rust,
Python, and TypeScript stacks; polyglot repos are fine.

Add the marketplace and install the plugin once, at user scope.

**Claude Code** — from any session:

```
/plugin marketplace add bmransom/foundry
/plugin install foundry@foundry
```

**Codex** — from a shell:

```
codex plugin marketplace add bmransom/foundry
codex plugin add foundry@foundry
```

Then bootstrap the target repo — `/foundry:bootstrap` in Claude Code, or ask Codex to
bootstrap foundry. It detects your stack, interviews you, installs the setup, and proves it
green before proposing a commit. It never overwrites an existing `AGENTS.md`, CI workflow,
or script: it merges additively, or reports the conflict and skips. On a version bump,
`foundry update` pulls template improvements and leaves your content untouched.

## Quickstart

`foundry bootstrap` runs in five gated phases — inspect → interview → copy → generate →
verify — and writes nothing until it has your answers. The interview asks:

- a one-paragraph project description;
- 5-10 domain terms (and the wrong names that keep cropping up) to seed the glossary;
- whether to exclude outside vocabulary (a neutral engine) or embrace it (a product);
- whether there's an API surface (HTTP, RPC, public library API);
- the gate commands your team already runs;
- whether parallel agents share this repo on one machine;
- for apps and services, the unit of work for logging (request, job, solve…);
- the first epic to head the board.

A run looks roughly like this:

```text
> /foundry:bootstrap
1 · Inspect    detected: Python (pyproject.toml · pytest · ruff), service, FastAPI entrypoint
2 · Interview  8 questions: description, domain terms, polarity, API surface, gates, …
3 · Copy       verbatim tooling + seed concepts written; .foundry/manifest.json recorded
4 · Generate   AGENTS.md, .foundry/bin/foundry shim + config, pin-free pre-push hook, CI
5 · Verify     vitepress build ✓   walking-skeleton scenario ✓   gate: PASS
proposed commit (asks first): chore(foundry): bootstrap engineering setup
```

From there, drive a card with `/foundry:code` in your session, or hand it to the driver
with `.foundry/bin/foundry run <card>`.

## Development

Foundry is self-hosted, built under its own conventions. Start here: `AGENTS.md` · the
board (`roadmap/ROADMAP.md`) · the foundry-v2 spec (`roadmap/specs/foundry-v2/`). Its own
gate runs the local tree: `uv run foundry gate`.

## Contributing

Open issues and pull requests. Foundry is self-hosted, so contributors follow its own
workflow: read `AGENTS.md` for the conventions and boundaries, run `uv run foundry gate`
before pushing, and add an eval case for any behavior-changing template or skill.
`roadmap/ROADMAP.md` tracks what's planned.

## Support

Questions and bug reports: open an issue on the
[issue tracker](https://github.com/bmransom/foundry/issues).

## License

[MIT](LICENSE) © Brandon Ransom
