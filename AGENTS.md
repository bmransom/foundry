# AGENTS.md — Foundry

Foundry is a Claude Code plugin (plus its marketplace) that bootstraps an AI-assisted
engineering setup into any repo: spec-driven development, executable Gherkin features, a
vitepress doc site, a tracked kanban board, a glossary-as-contract, verification gates,
and COE-driven eval accretion. Foundry ships the mechanisms; repos supply the content.

Foundry is self-hosted — developed under its own conventions. The board is
`roadmap/ROADMAP.md`; per-feature detail lives in `roadmap/specs/<feature>/`; vocabulary in
`knowledge/glossary.md`.

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
  `roadmap/specs/foundry-core/design.md` §Audit).
- Let a generated gate grade itself. Evals judge gates by discrimination — a seeded
  defect must make the gate fail — never by green-ness alone.

**Always**
- Before coining a canonical name (glossary term, public type or field, config knob),
  search the prior art and record provenance in `knowledge/glossary.md`.
- Keep foundry's verbatim-template copies byte-identical to
  `plugins/foundry/templates/verbatim/` (modulo the version marker) — the self-host gate.
- Give a behavior-changing template or skill an eval case before it ships.
- Close a COE only with a mechanical change (gate, lint, rule, or eval fixture), never
  prose.
- Run each card in its own git worktree on its `card/<id>` branch off the default branch
  (`git worktree add -b card/<id> wt/<id> origin/<default>`), never the shared primary
  checkout — a shared workspace overloads one branch across parallel sessions. Commit each
  green step freely (a local commit is a recoverable checkpoint); retire the worktree with
  `scripts/worktree-retire.sh` when the work lands.
- Write [Conventional Commits](https://www.conventionalcommits.org/) (`<type>(<scope>):
  <description>`, imperative mood); never claim a change is tested unless it was.
- Make surgical changes — touch only what the task requires; remove only what your change
  orphaned; flag unrelated issues, don't fix them silently.

**Ask first**
- Push to a remote, or merge to the default branch.

## Writing style

Strunk & White: omit needless words; use the active voice; make definite assertions.
Lead with the point; one idea per sentence; concrete commands, paths, and names; say it
once and link to depth. Prefer a table, list, or code block when denser than a sentence.
Context-resident prose (AGENTS.md, skills, agents, rules) loads every session — every
needless word costs tokens each time; cut hardest there.

## Task tracking

`roadmap/ROADMAP.md` is the board — the single source of truth for cross-spec status. Claim
a card by creating its `card/<id>` branch (its existence is the claim); a card is **Done
when its branch merges to the default branch with the gate green** — set Done in the
merging PR, never a separate follow-up. Specs live in `roadmap/specs/<feature>/`.

## Deeper docs

`knowledge/releasing.md` — how releases work · `roadmap/specs/foundry-core/` — v1 requirements and
design · `knowledge/glossary.md` — vocabulary · `roadmap/ROADMAP.md` — the board.
