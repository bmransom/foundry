<!-- foundry-seed: log v1 -->

# Knowledge log

Changes to the knowledge base, newest first. A reserved OKF file — no frontmatter.

## 2026-06-25

- **Fix** Bootstrap's `generate.md` vocab-lint guidance now scopes the generated
  `scripts/vocab-lint.sh` to **markdown prose** and excludes generated/dependency trees
  (`node_modules/`, `dist/`, lockfiles, the VitePress build). The lifecycle-e2e dogfood
  surfaced the gap: a fresh agent generated a recursive grep over `knowledge/` that
  false-matched the debt term `AI` inside `knowledge/package-lock.json`
  (`sponsors/ai`). The agent recovered, but the guidance now bakes the fix in so the
  next bootstrap gets it right unaided. The e2e harness gained a regression signal that
  flags a generated lint which fails to scope to prose.
- **New** Glossary terms **Autonomy level** and **Stop-point** for the `code` lifecycle's
  autonomy dial (`roadmap/specs/lifecycle-autonomy/`). The level (Supervised / Guided /
  Autonomous) decides who resolves a soft fork; the stop-point bounds an autonomous run.
  Set once at Frame, harness-aware (`/loop`, Codex `/goal`); the operational detail lives
  in `plugins/foundry/skills/code/references/autonomy.md`. Prior art: Codex approval modes
  + role-based agent-autonomy levels (autonomy level); the debugger breakpoint (stop-point).

## 2026-06-20

- **Update** Registered the **Code-review eval (L3)** in **Validation**
  (`evals/harness/code-review-eval.sh`) — manual, required green for a version
  bump; the A/B arm gates cross-model refuter enablement. No glossary entry: code
  review is generic prior art, provenance lives in the SKILL header (mirroring
  `spec-review`).

## 2026-06-19

- **Update** Added **Session storage tier** provenance for harness deliberation
  Tier 1 event ledger, Tier 2 immutable payloads, and Tier 3 rebuildable views.
- **Update** Recorded the opt-in harness deliberation live smoke command and
  PASS result in **Validation**.
- **Update** Clarified that `harness-status.py` is the stored-result label for
  **Harness availability**, not a separate glossary concept.
- **Update** Added harness-deliberation vocabulary: **Harness availability**, **Broker**, **Harness deliberation** (multi-agent debate/deliberation prior art, Foundry harness terminology), **Participant**, **Mediator**, and **Deferred dissent** for the new `roadmap/specs/harness-deliberation/` spec.

## 2026-06-16

- **Update** Added the **harness** term (an AI coding tool that runs foundry's skills; agent-harness-engineering vocabulary) and pointed the **Manifest** and **Convention version** entries at `.foundry/manifest.json` with the harness set — Wave 1 of harness-agnostic (`roadmap/specs/harness-agnostic/`).

## 2026-06-14

- **Update** Aligned the knowledge base to the Open Knowledge Format: `type` frontmatter (was `kind`), reserved `index.md` and `log.md`, and the `knowledge` tool and vocabulary.
