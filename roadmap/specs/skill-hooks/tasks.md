> **Status:** Backlog (2026-06-28) — drafted; parked on the open triggering-guarantee question (see [design.md](design.md) Open question); tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — skill-hooks

## Wave 1 — the stage-hook runner

- T1 `plugins/foundry/scripts/run-stage-hook.sh`: args `<stage> <phase>`; read
  `.foundry/hooks.json`'s `enabled` array; if `"<stage>.<phase>"` enabled, exec
  `.foundry/hooks/<stage>.<phase>.sh` with `{stage,phase,feature,branch,autonomy}` JSON on stdin;
  exit 0 → proceed, non-zero → block (signalled to the caller); warn + fail on
  enabled-but-missing / non-executable (AC-1.1–1.6, AC-2.1, AC-2.2, AC-2.4).
- T2 `tests/run_stage_hook_test.sh` (hermetic): enabled `verify.pre` returns non-zero → block
  with reason; disabled / absent → proceed unchanged (AC-2.3); enabled-but-missing → warn+fail.
  Discrimination both ways (AC-4.3).
- Gate: the test passes; no live agent run.

## Wave 2 — wire into the lifecycle + the consumer config

- T3 `plugins/foundry/skills/code/SKILL.md` + `references/hooks.md`: run `run-stage-hook.sh
  <stage> pre` before the stage and `post` after, when enabled (AC-1.2, AC-1.3; pre non-zero →
  block the stage: AC-1.4; post non-zero → fail the gate: AC-1.5); document the convention, the
  `.foundry/hooks.json` schema, the per-boundary context fields, and the **advisory-strength vs.
  gate** boundary (AC-3.1, AC-4.1). Keep `SKILL.md` within budget — detail in the reference.
- T4 `.foundry/hooks.json` + bootstrap seed: an `enabled` array (consumer-owned, **not** the
  managed manifest — the telemetry-opt-in precedent); bootstrap seeds `.foundry/hooks/` (with a
  commented example) + an empty `.foundry/hooks.json` (AC-4.2).
- Gate: `knowledge.py` clean; bootstrap verify still green; the `.foundry/hooks.json` schema documented.

## Wave 3 — boundary doc + eval

- T5 `references/hooks.md` (or a `code` skill note): document that tool-level gating uses the
  harness's native hooks (Claude/Codex `hooks.json`, pi extensions) — Foundry builds no adapter
  (AC-3.2). Link the harness docs.
- T6 An eval/test fixture proving the end-to-end stage block: a fixture repo with an enabled
  `verify.pre` that fails → the lifecycle halts Verify; flip disabled → it proceeds (AC-4.3). May
  reuse T2's harness if a live run is too costly.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; glossary `Stage hook` row + provenance.
