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
- T6 The `card-ids` discrimination is gate-proven by the existing `scripts/test_check_board.py`
  (`test_claimable_missing_id_fails`, `test_missing_id_column_fails`, blank-id-on-Done passes) —
  the state the migration restores; the detector is idempotent by construction (it keys on the
  absent `Id` column the migration adds), matching the other migrations' no-unit-test convention
  (AC-4.1, AC-4.2, AC-4.3).
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; `Gate tool` glossary row + `log.md` entry.

## Wave 4 — self-host the check (US-5, Foundry-local)

- T7 `scripts/check-gate-tools.sh` (+ wire into `check-fast.sh`): assert every
  `foundry-gate-tool`-marked `scripts/*` is referenced
  in `check-fast.sh`, and that the migration registry head equals `.foundry/manifest.json`
  `conventionVersion` — fail the gate otherwise (AC-5.1, AC-5.2). Foundry-local; **not** a
  verbatim template.
- T8 An `AGENTS.md` Boundary (Foundry-local — it is Foundry's own contract): a convention break
  (board / template / frontmatter structure change) ships with a migration + registry bump, so
  `code-review` flags a PR that omits it (AC-5.3).
- T9 `tests/check_gate_tools_test.sh`: a marked script missing from `check-fast.sh` fails the
  lint; a drifted `conventionVersion` fails it; the wired/in-sync state passes (discrimination).
- Gate: `check-fast.sh` runs `check-gate-tools.sh` and stays green on Foundry itself.
