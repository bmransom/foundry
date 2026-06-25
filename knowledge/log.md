<!-- foundry-seed: log v1 -->

# Knowledge log

Changes to the knowledge base, newest first. A reserved OKF file — no frontmatter.

## 2026-06-24

- **Convention** Wiring a PostToolUse convergence trigger (`spec-convergence-posttooluse.sh`,
  and a future `code-review-posttooluse.sh`): scope it with BOTH layers — the Claude Code
  hook `if` field (native path filter, e.g. `Edit(/roadmap/specs/**/*.md)|Write(…)|MultiEdit(…)`;
  the `matcher` matches tool names only) AND the adapter's own in-script path filter. The
  `if` field is Claude-Code-only, so the in-script filter is the harness-agnostic correctness
  guarantee (Codex has no `if`). Verify the installed Claude Code version supports `if` before
  relying on it. Source: code.claude.com/docs/en/hooks.md#path-based-filtering.

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
