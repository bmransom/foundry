# Foundry

[![CI](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml/badge.svg)](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml)
[![Release](https://img.shields.io/github/v/release/bmransom/foundry)](https://github.com/bmransom/foundry/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code plugin that bootstraps an AI-assisted engineering setup into any repo:
spec-driven development, executable acceptance tests, a verification gate on every
push, a glossary-as-contract, and an OKF-aligned knowledge base. It wires the setup to
your stack and proves it green before the first commit. Foundry ships the mechanisms;
your repo supplies the content.

## Contents

- [Why](#why)
- [What foundry installs](#what-foundry-installs)
- [The plugin](#the-plugin)
- [Setup](#setup)
- [Quickstart](#quickstart)
- [Development](#development)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## Why

Engineering discipline arrives late, if at all: specs after the code, tests after the
bug, a gate after the outage. Foundry installs it on day one, wired to your stack, so
an agent or a human works against real gates from the first commit. A reference repo
proves the mechanisms; a versioned plugin ships them.

## What foundry installs

`/foundry:bootstrap` detects your stack and installs a setup your repo then owns:

| Capability | Where |
|---|---|
| Spec-driven workflow: requirements → design → tasks, in EARS | `roadmap/specs/` |
| Executable Gherkin features through a real entrypoint, no mocks | `features/` |
| OKF-aligned knowledge base plus the `knowledge` navigation tool | `knowledge/` |
| Glossary-as-contract: the vocabulary the agent must use | `knowledge/glossary.md` |
| Tracked kanban board: the single source of truth for status | `roadmap/ROADMAP.md` |
| Verification gate, wired to a pre-push hook and CI | `scripts/check-fast.sh` |
| Conventions, gates, and boundaries (plus a `CLAUDE.md` symlink) | `AGENTS.md` |
| Vitepress doc site rendering the knowledge base | `knowledge/.vitepress/` |

The knowledge base follows the
[Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf):
plain markdown concepts (`type` frontmatter) with a generated listing and a change
log. It stays portable, not locked to the doc site.

## The plugin

Installed once at user scope, these run in every repo:

| Component | What it does |
|---|---|
| `/foundry:bootstrap` | Installs the setup into the current repo: inspect → interview → copy → generate → verify |
| `/foundry:update` | Refreshes installed templates on a version bump; never overwrites your content |
| `code` skill | Drives feature work: spec → plan → build → verify → finish |
| `performance` skill | Treats performance-sensitive work as a lifecycle concern: baseline → benchmark → profile → attribute |
| `naming-standards` skill | Reviews glossary, API, file, metric, and config names before they become contracts |
| `design-patterns` skill | Chooses patterns such as Strategy, Adapter, Observer, Factory, Builder, Facade, Decorator, Command, and State when they earn their complexity |
| `modular-structure` skill | Reviews directory layout, module boundaries, dependency direction, and public/internal APIs |
| `spec-review` skill | Reviews specs and context-resident prose against the glossary and writing style, preferably in fresh context |
| `handoff` skill | Captures verified state and starts a same-harness successor session |
| `extract-skill` skill | Distills reusable workflows from a session into user, repo, or plugin skills |

## Setup

**Requirements:** [Claude Code](https://docs.claude.com/en/docs/claude-code) or
[Codex](https://developers.openai.com/codex), and a git repository. Bootstrap wires
Rust, Python, and TypeScript stacks; polyglot repos are fine.

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

Then, in the repo you want to set up, run the bootstrap skill — `/foundry:bootstrap` in
Claude Code, or ask Codex to bootstrap foundry into the repo.

It detects your stack, interviews you, installs the setup, and proves it works before
it proposes a commit. It never overwrites an existing `AGENTS.md`, CI workflow, or
script: it merges additively, or reports the conflict and skips. When the plugin
version bumps, `/foundry:update` pulls template improvements and leaves your content
untouched.

## Quickstart

`/foundry:bootstrap` runs in five gated phases (inspect → interview → copy → generate
→ verify) and writes nothing until it has your answers. The interview asks:

- a one-paragraph project description;
- 5-10 domain terms (and the wrong names that keep cropping up) to seed the glossary;
- whether to exclude outside vocabulary (a neutral engine) or embrace it (a product);
- whether there's an API surface (HTTP, RPC, public library API);
- the gate commands your team already runs;
- whether parallel agents share this repo on one machine;
- for apps and services, the unit of work for logging (request, job, solve…);
- the first epic to head the board.

A run looks roughly like this:

<!-- Tip: record a real run with `asciinema rec` and embed the player link here. -->

```text
> /foundry:bootstrap
1 · Inspect    detected: Python (pyproject.toml · pytest · ruff), service, FastAPI entrypoint
2 · Interview  8 questions: description, domain terms, polarity, API surface, gates, …
3 · Copy       verbatim tooling + seed concepts written; .foundry-manifest.json recorded
4 · Generate   AGENTS.md, scripts/check-fast.sh, features/, CI, wired to your stack
5 · Verify     vitepress build ✓   walking-skeleton scenario ✓   check-fast: PASS
proposed commit (asks first): foundry: bootstrap engineering setup
```

The `code` lifecycle skill and `spec-review` then drive every feature in the repo.

## Development

Foundry is self-hosted, built under its own conventions. Start here: `AGENTS.md` · the
board (`roadmap/ROADMAP.md`) · the foundry-core spec (`roadmap/specs/foundry-core/`).

## Contributing

Open issues and pull requests. Foundry is self-hosted, so contributors follow its own
workflow: read `AGENTS.md` for the conventions and boundaries, run
`scripts/check-fast.sh` before pushing, and add an eval case for any behavior-changing
template or skill. `roadmap/ROADMAP.md` tracks what's planned.

## Support

Questions and bug reports: open an issue on the
[issue tracker](https://github.com/bmransom/foundry/issues).

## License

[MIT](LICENSE) © Brandon Ransom
