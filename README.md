# Foundry

[![CI](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml/badge.svg)](https://github.com/bmransom/foundry/actions/workflows/check-fast.yml)
![Version](https://img.shields.io/badge/version-1.0.0-blue.svg) <!-- x-release-please-version -->
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A Claude Code plugin that bootstraps an AI-assisted engineering setup into any repo:
spec-driven development, executable Gherkin features, a vitepress doc site, a tracked
kanban board, a glossary-as-contract, verification gates, and COE-driven eval
accretion. It ships the mechanisms; your repo supplies the content.

## Contents

- [Why](#why)
- [Setup](#setup)
- [Quickstart](#quickstart)
- [Development](#development)
- [Contributing](#contributing)
- [Support](#support)
- [License](#license)

## Why

Engineering discipline — specs before code, executable acceptance tests, a
verification gate on every push, a vocabulary that stays consistent, a doc site that
stays current — usually gets bolted onto a repo years in, if ever. Foundry installs it
on day one and wires it to your stack, so an agent (or a human) works against real
gates from the first commit. The mechanisms are proven on a reference repo and shipped
as a versioned plugin; your repo supplies the domain content.

## Setup

**Requirements:** [Claude Code](https://docs.claude.com/en/docs/claude-code) and a git
repository. Bootstrap wires Rust, Python, and/or TypeScript stacks — polyglot repos
are fine.

One time, from any Claude Code session, add the marketplace and install the plugin:

```
/plugin marketplace add bmransom/foundry
/plugin install foundry@foundry
```

Then, in the repo you want to set up, run the bootstrap:

```
/foundry:bootstrap
```

It detects your stack, interviews you, installs the setup, and proves it works before
proposing a commit — it never overwrites an existing `AGENTS.md`, CI workflow, or
script (it merges additively, or reports the conflict and skips). When the plugin
version bumps later, run `/foundry:update` to pull template improvements.

## Quickstart

`/foundry:bootstrap` runs in five gated phases — inspect → interview → copy →
generate → verify — and writes nothing until it has your answers. The interview asks:

- a one-paragraph project description;
- 5–10 domain terms (and the wrong names that keep cropping up) to seed the glossary;
- whether to exclude outside vocabulary (a neutral engine) or embrace it (a product);
- whether there's an API surface (HTTP, RPC, public library API);
- the gate commands your team already runs;
- whether parallel agents work in this repo on one machine;
- for apps and services, the unit of work for logging (request, job, solve…);
- the first epic to head the board.

A run looks roughly like this:

<!-- Tip: record a real run with `asciinema rec` and embed the player link here. -->

```text
> /foundry:bootstrap
1 · Inspect    detected: Python (pyproject.toml · pytest · ruff), service, FastAPI entrypoint
2 · Interview  8 questions — description, domain terms, polarity, API surface, gates, …
3 · Copy       verbatim tooling + seed docs written; .foundry-manifest.json recorded
4 · Generate   AGENTS.md, scripts/check-fast.sh, features/, CI — wired to your stack
5 · Verify     vitepress build ✓   walking-skeleton scenario ✓   check-fast: PASS
proposed commit (asks first): foundry: bootstrap engineering setup
```

When it finishes you have, wired to your detected stack and verified green:

- `AGENTS.md` (plus a `CLAUDE.md` symlink) carrying your conventions, gates, and vocabulary;
- a spec workflow in `specs/` and executable Gherkin features in `features/`, with a
  walking-skeleton scenario through a real production entrypoint;
- a vitepress doc site, a tracked kanban board (`docs/ROADMAP.md`), and a
  glossary-as-contract (`docs/glossary.md`);
- a verification gate (`scripts/check-fast.sh`) wired to a pre-push hook and to CI.

A generalized `code` lifecycle skill and a `spec-reviewer` agent ship with the plugin
and apply in every bootstrapped repo.

## Development

Foundry is self-hosted — developed under its own conventions. Start here: `AGENTS.md`
· the board in `docs/ROADMAP.md` · the v1 spec in `specs/foundry-core/`.

## Contributing

Issues and pull requests are welcome. Foundry is self-hosted, so the contributor
workflow is foundry's own: read `AGENTS.md` for the conventions and boundaries, run
`scripts/check-fast.sh` before pushing, and add an eval case for any template or skill
change that alters behavior. The board in `docs/ROADMAP.md` tracks what's planned.

## Support

Questions and bug reports: open an issue on the
[issue tracker](https://github.com/bmransom/foundry/issues).

## License

[MIT](LICENSE) © Brandon Ransom
