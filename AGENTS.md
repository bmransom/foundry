# AGENTS.md — Foundry

Foundry is a Claude Code plugin (plus its marketplace) that bootstraps an AI-assisted
engineering setup into any repo: spec-driven development, executable Gherkin features, a
vitepress doc site, a tracked kanban board, a glossary-as-contract, verification gates,
and COE-driven eval accretion. Foundry ships the mechanisms; repos supply the content.

Foundry is self-hosted — developed under its own conventions. The board is
`docs/ROADMAP.md`; per-feature detail lives in `specs/<feature>/`; vocabulary in
`docs/glossary.md`.

## Commands

```bash
scripts/check-fast.sh                      # the quick gate: plugin validate + byte-identity + script tests
scripts/install-hooks.sh                   # once per clone: route git hooks through .githooks/
claude plugin validate plugins/foundry     # manifest check only (runs inside the gate)
```

The gate runs from `.githooks/pre-push` and from CI (`.github/workflows/check-fast.yml`):
one script, two triggers. Bypass once with `git push --no-verify`.

## Boundaries

**Never**
- Put repo-specific content in a template. Templates carry mechanisms and patterns;
  entity models, forbidden terms, standing rules, and gate commands come from the
  bootstrap interview or accrete in the consumer repo (the mechanisms-not-content rule,
  `specs/foundry-core/design.md` §Audit).
- Let a generated gate grade itself. Evals judge gates by discrimination — a seeded
  defect must make the gate fail — never by green-ness alone.

**Always**
- Before coining a canonical name (glossary term, public type or field, config knob),
  search the prior art and record provenance in `docs/glossary.md`.
- Keep foundry's verbatim-template copies byte-identical to
  `plugins/foundry/templates/verbatim/` (modulo the version marker) — the self-host gate.
- Give a behavior-changing template or skill an eval case before it ships.
- Close a COE only with a mechanical change (gate, lint, rule, or eval fixture), never
  prose.

**Ask first**
- Commit or push. Branch first on the default branch.

## Writing style

Strunk & White: omit needless words; use the active voice; make definite assertions.
Lead with the point; one idea per sentence; concrete commands, paths, and names; say it
once and link to depth. Prefer a table, list, or code block when denser than a sentence.
Context-resident prose (AGENTS.md, skills, agents, rules) loads every session — every
needless word costs tokens each time; cut hardest there.

## Task tracking

`docs/ROADMAP.md` is the board — the single source of truth for cross-spec status. Claim
a card by setting its owner; `Done` requires a recorded gate PASS. Specs live in
`specs/<feature>/`.

## Deeper docs

`docs/releasing.md` — how releases work · `specs/foundry-core/` — v1 requirements and
design · `docs/glossary.md` — vocabulary · `docs/ROADMAP.md` — the board.
