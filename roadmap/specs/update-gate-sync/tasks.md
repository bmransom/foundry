> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — update-gate-sync

## Wave 1 — gate tools self-declare

- T1 Add a `# foundry-gate-tool: <invocation>` marker to `scripts/check-board.py` (its bare gate
  line) and `scripts/prose-lint.py` (its **full** gate line, including the `! -name index.md`
  exclusion), and to their `plugins/foundry/templates/verbatim/scripts/` twins — byte-identical
  (AC-1.1, AC-1.2).
- Gate: byte-identity twins green; existing `test_check_board.py` / `test_prose_lint.py` pass.

## Wave 2 — both delivery paths read the marker

- T2 `plugins/foundry/skills/bootstrap/references/generate.md`: derive the generated gate's tool
  list from the `foundry-gate-tool` markers (wire every marked tool, in a stable order), closing
  the `prose-lint.py` omission (AC-1.3, AC-2.1, AC-2.2).
- T3 `plugins/foundry/skills/update/SKILL.md`: add a **gate-sync** step — read the gate command
  from `AGENTS.md` Commands, and for each installed marked gate tool, grep that gate for the
  script; flag any unwired tool in the §6 report with its marker snippet, and offer to apply on
  go-ahead (never silent) (AC-1.3, AC-3.1, AC-3.2, AC-3.3, AC-3.4).
- Gate: a `tests/gate_sync_test.sh` — an unwired marked tool is flagged with its snippet; a wired
  one is not (discrimination, AC-3.4).

## Wave 3 — the card-ids migration

- T4 `plugins/foundry/skills/update/references/migrations/card-ids.md` (convention 4): detector =
  a board whose card tables lack the `Id` column (or manifest `conventionVersion < 4`); transform
  = backfill a unique slug-safe `Id` on every claimable card (judgment: derive the slug from the
  card's Work); self-verify = the detector no longer fires and every claimable card has a unique
  `Id`, checked via the plugin's **bundled** `check-board.py` (the repo's copy + gate wiring
  arrive later, in update §4/§6 + gate-sync) (AC-4.1, AC-4.2, AC-4.3).
- T5 `references/migrations/README.md`: add the convention-4 `card-ids` row; bump the head to 4.
  Stamp Foundry's own `.foundry/manifest.json` `conventionVersion: 4` (AC-4.4, AC-4.5).
- T6 `tests/`: the `card-ids` detector fires on a pre-`Id` fixture board and is idempotent after
  backfill; the bundled `check-board.py` flips fail→pass (AC-4.1, AC-4.2, AC-4.3).
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; `Gate tool` glossary row + `log.md` entry.
