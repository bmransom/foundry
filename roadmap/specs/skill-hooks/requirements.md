> **Status:** Backlog (2026-06-28) — drafted; parked on the open triggering-guarantee question (see [design.md](design.md) Open question); tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — skill-hooks

## Summary

Let a consuming repo customize the `code` SDLC at **stage boundaries** — a custom Verify gate,
a Finish step, a Spec-time check — without forking Foundry. A consumer drops an executable at a
well-known path (`.foundry/hooks/<stage>.<pre|post>.sh`), enables it in `.foundry/hooks.json`,
and the lifecycle runs it at that boundary; a `pre` hook can block the stage. Web research
(2026-06-28): the SDLC stages are **skill-orchestrated, not harness tool-events**, so this is a
Foundry convention (harness-agnostic by construction) — not a wrapper over the harnesses' native
tool hooks. Tool-level gating stays the harness's native job (documented, not rebuilt).

## Glossary impact

- **Stage hook** — a consumer-supplied script the `code` lifecycle runs at a named stage
  boundary (`<stage>.pre` before, `<stage>.post` after). Prior art: Claude Code / Codex
  `hooks.json` (tool-event hooks) and git hooks — this names the SDLC-stage analogue. Provenance
  recorded in `knowledge/glossary.md`.

## US-1 — The stage-hook convention

- AC-1.1 A consumer SHALL supply a stage hook at `.foundry/hooks/<stage>.<pre|post>.sh`, where
  `<stage>` is a `code`-lifecycle stage (`frame`/`spec`/`plan`/`build`/`verify`/`knowledge`/`review`/`finish`).
- AC-1.2 THE `code` lifecycle SHALL run an enabled `<stage>.pre` hook before entering the stage.
- AC-1.3 THE `code` lifecycle SHALL run an enabled `<stage>.post` hook after the stage's work.
- AC-1.4 WHEN a `pre` hook exits non-zero, THE lifecycle SHALL NOT enter the stage (it blocks).
- AC-1.5 WHEN a `post` hook exits non-zero, THE stage's gate SHALL be treated as failed.
- AC-1.6 THE lifecycle SHALL pass the hook a JSON context on **stdin** (stage, phase, feature,
  branch, autonomy) — config as data, adding no new environment variable.

## US-2 — Opt-in, safe, zero-config-by-default

- AC-2.1 A hook SHALL run only when listed in `.foundry/hooks.json`'s `enabled` array — a hook
  file alone SHALL NOT auto-run (a dropped-in or stray script never executes implicitly).
  Enablement is a consumer-owned config, **not** the managed `.foundry/manifest.json` lockfile
  (the telemetry opt-in precedent — a consumer toggle lives off the lockfile).
- AC-2.2 WHEN an enabled hook path is missing or not executable, THE lifecycle SHALL surface a
  warning and treat it as a failed configuration, not silently skip it.
- AC-2.3 WHEN a stage has no enabled hook, THE lifecycle SHALL proceed unchanged — an existing
  repo with no `enabled` array (or no `.foundry/hooks.json`) behaves identically to today.
- AC-2.4 A hook's stdout/stderr SHALL surface in the lifecycle output, so a blocked stage shows
  the hook's reason.

## US-3 — Enforcement boundary stays honest

- AC-3.1 THE design SHALL state that skill-run stage hooks are **advisory-strength** (the agent
  runs them per the lifecycle) and that the repo **gate** (`check-fast`, branch-protected) is the
  hard enforcement boundary — a consumer needing hard Verify enforcement adds their check to the
  gate, with `verify.post` as the local mirror.
- AC-3.2 Foundry SHALL NOT build per-harness adapters over the harnesses' native tool hooks;
  tool-level gating is delegated to the harness (Claude/Codex `hooks.json`, pi extensions) and
  documented, not rebuilt.

## US-4 — Propagation + discrimination

- AC-4.1 THE convention SHALL be documented in a `code` skill reference (`references/hooks.md`).
- AC-4.2 THE convention SHALL be carried in the bootstrap seed, so a new repo gets
  `.foundry/hooks/` + the `.foundry/hooks.json` schema.
- AC-4.3 AN eval/test SHALL prove a non-zero `verify.pre` hook blocks Verify and that a repo
  with no enabled hook runs the stage unchanged (discrimination both ways).

## Metrics

- A blocking `pre` hook halts the stage with its reason shown; a `post` non-zero fails the gate.
- Zero-config default: no `enabled` array → byte-identical lifecycle behavior.
- A hook file present but not enabled in `.foundry/hooks.json` never runs (the opt-in safety gate).
