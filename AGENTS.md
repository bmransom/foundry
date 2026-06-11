# AGENTS.md — Foundry

Foundry is a Claude Code plugin (plus its marketplace) that bootstraps an AI-assisted
engineering setup into any repo: spec-driven development, executable Gherkin features,
a vitepress doc site with frontmatter-driven discovery, a tracked kanban board, a
glossary-as-contract, verification gates, and COE-driven eval accretion. Octant
(`~/dev/workspace/octant`) is the reference implementation the conventions are
extracted from; foundry ships the mechanisms, repos supply the content.

Foundry is self-hosted: this repo is developed with its own conventions. The board is
`docs/ROADMAP.md`; per-feature detail lives in `specs/<feature>/`; vocabulary in
`docs/glossary.md`.

## Commands

```bash
scripts/check-fast.sh                      # the quick gate: plugin validate + byte-identity + script tests
scripts/install-hooks.sh                   # once per clone: route git hooks through .githooks/
claude plugin validate plugins/foundry     # manifest check only (runs inside the gate)
```

The gate runs from `.githooks/pre-push` (bypass once with `git push --no-verify`) and
from CI (`.github/workflows/check-fast.yml`) — same script, two triggers.

## Boundaries

**Never**
- Put repo-specific content in a template. Templates carry mechanisms and patterns;
  entity models, forbidden terms, standing rules, and gate commands come from the
  bootstrap interview or accrete in the consumer repo (the mechanisms-not-content rule,
  `specs/foundry-core/design.md` §Audit).
- Let a generated gate grade itself. Evals judge gates by discrimination — a seeded
  defect must make the gate fail — never by green-ness alone.

**Always**
- Before coining a canonical name (glossary term, public type or field, config
  knob), search the prior art — domain literature, stack naming conventions,
  comparable tools. Prefer the established term; record provenance in
  `docs/glossary.md`.
- Keep foundry's own copies of verbatim-template files byte-identical to
  `plugins/foundry/templates/` (modulo the version marker) — the self-host gate.
- A template or skill change that alters behavior needs an eval case before it ships.
- A COE is closed only by a mechanical change (gate, lint, rule, or eval fixture),
  never by prose alone.

**Ask first**
- Commit or push. Branch first if on the default branch.

## Writing style

The standard is Strunk & White: omit needless words; use the active voice; make
definite assertions. Lead with the point; one idea per sentence; concrete commands,
paths, and names; say it once and link to depth. Prefer a table, list, or code block
when denser than a sentence. Plugin-resident prose (skills, agents, rules, templates)
loads into context windows — every needless word costs tokens in every session that
loads it; cut hardest there.

## Task tracking

`docs/ROADMAP.md` is the tracked kanban board — the single source of truth for
cross-spec status. Claim a card by setting its owner; `Done` requires a recorded gate
PASS once the gate exists. Specs are tracked in `specs/<feature>/`.

## Deeper docs

`specs/foundry-core/` — requirements and design for foundry v1 ·
`docs/glossary.md` — foundry's own vocabulary · `docs/ROADMAP.md` — the board.
