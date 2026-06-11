---
name: bootstrap
description: Use when explicitly asked to bootstrap, install, or set up the
  foundry engineering setup in a repo (/foundry:bootstrap) — specs, executable
  features, docs site, board, glossary, gates, and CI, wired to the repo's
  stack and verified working. Not for feature work in a bootstrapped repo.
---

# Bootstrap

Install the foundry setup into the current repo in five phases. Templates ship
with the plugin at `<base dir>/../../templates/` — `verbatim/` (byte-exact
tooling) and `seeds/` (content starting points the repo will own).

Copy into your reply; check off as you go. A gate is a **prohibition**: do not
start a later phase until the prior gate is met.

- [ ] **1 Inspect** — detect the stack, entrypoints, repo shape. GATE: write the detection report before asking any questions.
- [ ] **2 Interview** — collect the repo's content. GATE: no files written until every answer is recorded.
- [ ] **3 Copy** — verbatim templates byte-exact; seeds filled. GATE: no edits inside a verbatim copy.
- [ ] **4 Generate** — the stack-aware files per `references/generate.md`. GATE: no invented commands — every gate command was detected or confirmed.
- [ ] **5 Verify** — prove it per `references/verify.md`. GATE: no commit without a pasted PASS, a seen failure, and the caller's go-ahead.

## 1 · Inspect

Detect and report before asking anything:

- Languages and tools: Cargo.toml, pyproject.toml, package.json, lockfiles,
  configured linters and test frameworks.
- Production entrypoints: binaries, console scripts, served apps, exported
  library APIs.
- Repo shape: service/app, library, or CLI.
- What already exists: AGENTS.md, CLAUDE.md, CI workflows, hooks, docs.

**The repo owns its existing files.** Never overwrite an existing AGENTS.md, CI
workflow, or script: merge additively where a section is missing; otherwise
report the conflict and skip the file.

## 2 · Interview

Ask through the host's question tool when one is present; accept canned answers
when the caller supplies them. The questions:

1. One-paragraph project description.
2. 5–10 domain terms — and the wrong names that keep appearing (they seed the
   glossary and its debt column).
3. Vocabulary polarity: exclude outside domain vocabulary (a neutral engine) or
   embrace it (a product)?
4. Is there an API surface (HTTP, RPC, public library API)?
5. Gate commands the team already runs (confirm what Inspect detected).
6. Will parallel agents work in this repo on one machine?
7. Apps and services only: the unit of work for logging (request, job, solve…).
8. The first epic — the milestone that heads the board.

## 3 · Copy

- Copy every `verbatim/` file to the same relative path, byte-exact — the
  `foundry-template: <name> v<N>` markers included; `/foundry:update` diffs
  depend on them. Keep scripts executable.
- Copy `seeds/` files, then fill them from the interview: glossary terms, debt
  column, and polarity statement; the first ROADMAP epic; the
  `docs/.vitepress/site.json` title and description. Keep the `foundry-seed:`
  markers.

## 4 · Generate

Read `references/generate.md` first — it carries the AGENTS.md skeleton and
every per-stack mapping. Produce:

- `AGENTS.md` from the skeleton, filled with detected + interview content; then
  `ln -s AGENTS.md CLAUDE.md` — a symlink, not a copy.
- `scripts/check-fast.sh` wired to the repo's real commands. Commands must be
  repo-portable: discover project-local toolchains (venv, `node_modules/.bin`)
  at runtime; never hardcode machine paths. CI installs dependencies first.
- `scripts/verify.sh` + machine-global lock — only when an expensive validation
  exists — see `references/generate.md` §verify.sh.
- `features/` + the stack's BDD runner + one walking-skeleton Scenario through
  a real production entrypoint — no mocks.
- A CI workflow running the same gate, plus a docs-build job.
- AGENTS.md Contracts section — only when the interview named an API surface.
- AGENTS.md Logging section + library wiring + one working example event —
  apps and services only.
- The isolation pattern matching the repo shape and parallel-agents answer.
- `scripts/vocab-lint.sh` — only when the glossary debt column has entries.

## 5 · Verify

Read `references/verify.md`; run its checklist end to end and paste each
output: file inventory, hooks installed, vitepress build, walking-skeleton
Scenario green, `check-fast: PASS`.

The gate must also **discriminate**: seed a failing check, watch the gate fail,
remove the seed, watch it pass.

Then review `git status`, propose the commit with explicit paths, and **ask
before committing**.
