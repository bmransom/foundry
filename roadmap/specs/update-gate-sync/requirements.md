> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — update-gate-sync

## Summary

Make Foundry's delivery of **gate tools** (a verbatim script that belongs in a repo's gate,
like `check-board.py` or `prose-lint.py`) self-describing, so both `bootstrap` and `update`
wire them — closing the gap where a consumer running `foundry:update` gets the new scripts as
*inert files* their gate never runs. Today the wiring is two hardcoded lists that drift:
`generate.md` wires `check-board.py` but **not** `prose-lint.py`, and `update` wires nothing
into an existing repo's gate at all. The fix: a gate tool **self-declares** via a marker; both
paths read it. Plus a one-time `card-ids` migration to backfill the now-required board `Id`s.

## Glossary impact

- **Gate tool** — a Foundry-shipped verbatim script that belongs in a consumer repo's **Gate**
  (e.g. `check-board.py`, `prose-lint.py`). Prior art: a CI check / pre-commit hook (a script a
  build gate runs); Foundry names the subset it ships and wires. Extends the existing `Gate`
  term; provenance recorded in `knowledge/glossary.md`. The `# foundry-gate-tool:` marker is a
  sibling of the existing `foundry-template:` / `foundry-seed:` markers — no new concept,
  recorded in `log.md`.

## US-1 — Gate tools self-declare

- AC-1.1 A verbatim script that belongs in the gate SHALL carry a `# foundry-gate-tool: <invocation>`
  marker, where `<invocation>` is the tool's **literal gate command line** — including any
  exclusion (e.g. prose-lint's `! -name index.md`) — so the marker reproduces the exact wiring.
- AC-1.2 `scripts/check-board.py` and `scripts/prose-lint.py` (and their verbatim twins) SHALL
  carry the marker.
- AC-1.3 THE marker SHALL be the single source of truth for "this script belongs in the gate" —
  adding a future gate tool requires only the marker, with no list to edit in `generate.md` or
  the `update` skill.

## US-2 — Bootstrap wires every gate tool

- AC-2.1 `bootstrap`'s `generate.md` SHALL wire **every** marked gate tool into the generated
  gate (`check-fast.sh`), derived from the markers — not a hardcoded subset.
- AC-2.2 A freshly bootstrapped repo's gate SHALL therefore reference both `check-board.py` and
  `prose-lint.py` (the current omission of `prose-lint.py` is closed).

## US-3 — Update verifies gate wiring (gate-sync)

- AC-3.1 During `update`, for each installed marked gate tool, the skill SHALL check the repo's
  gate (the command `AGENTS.md` Commands names) for that script and flag any installed
  gate tool the gate does not run.
- AC-3.2 A flagged tool's report entry SHALL carry its wiring snippet (the marker's gate line).
- AC-3.3 THE skill SHALL apply the wiring only on the caller's go-ahead, and SHALL NOT silently
  edit the repo-owned gate.
- AC-3.4 A gate tool the gate already runs SHALL NOT be flagged (no false positive).

## US-4 — The card-ids migration (convention 4)

- AC-4.1 A `card-ids` migration SHALL backfill a unique slug-safe `Id` on every **claimable**
  card (Ready / In progress / Validating) of a pre-`Id` board, so `check-board.py` passes where
  it previously failed.
- AC-4.2 THE migration detector SHALL fire on a board whose card tables lack the `Id` column (or
  a manifest `conventionVersion < 4`).
- AC-4.3 AFTER a successful backfill, THE detector SHALL NOT re-fire (idempotent).
- AC-4.4 THE migration registry head SHALL become convention 4.
- AC-4.5 Foundry's own manifest `conventionVersion` SHALL be stamped 4.

## US-5 — Self-host: Foundry's own gate catches the drift (not a review reminder)

A mechanical, **Foundry-local** check (rationale in [design.md](design.md)) — it lives in
Foundry's gate, not the shipped `code-review` skill.

- AC-5.1 A self-host check in Foundry's gate SHALL assert every `foundry-gate-tool`-marked script
  under `scripts/` is wired into `check-fast.sh`, failing the gate if a marked tool is unwired
  (the deterministic dogfood of `gate-sync`).
- AC-5.2 THE self-host check SHALL assert the migration registry head equals Foundry's manifest
  `conventionVersion`, failing the gate if a convention shipped without its registry bump.
- AC-5.3 A repo-contract entry (an `AGENTS.md` Boundary or a `rules/` file) SHALL require that a
  convention break (a board / template / frontmatter structure change) ships with a migration +
  registry bump, so `code-review` — which reads the contract — flags a PR that omits it (the
  irreducibly-judgment part).

## Metrics

- A freshly bootstrapped gate references both `check-board.py` and `prose-lint.py` (AC-2.2).
- An existing consumer with an unwired gate tool gets it flagged with its snippet; a wired tool
  is not flagged (AC-3.1/3.4 discrimination).
- The `card-ids` migration backfills `Id`s so `check-board.py` passes on a board that failed
  before; an already-`Id` board does not re-trigger (AC-4.1/4.2/4.3).
- Foundry's own gate fails if a `foundry-gate-tool`-marked script is added without wiring it into
  `check-fast.sh`, or if `conventionVersion` drifts from the registry head (AC-5.1/5.2).
