> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — reviewer-effort

## Summary

A neutral **effort/model** knob on the fresh-session spawn, mapped per harness, threaded
through the review wrappers — so the **adversarial cross-family pass can run at a higher
effort than the primary review**: differential reasoning where reliability matters most.
Today `spawn-fresh-session.sh` launches a bare `claude`/`codex` with no effort or model
control, so every review runs at the harness's session default. Builds on
[`review-convergence`](../review-convergence/requirements.md)'s cross-family pass; motivated by
the hypothesis (eval-gated in US-3) that more reasoning raises judge reliability.

## Glossary impact

- **Effort level** — the reasoning budget a harness spends on a turn (`low`/`medium`/`high`/…).
  Reuses the harness CLIs' own vocabulary (`claude --effort`, OpenAI/codex
  `model_reasoning_effort`); a harness pass-through (like the existing `--skip-permissions`
  flag and `review-convergence`'s `blocking`/`advisory`), not a new Foundry concept — no
  glossary row, to be recorded in `knowledge/log.md` (T6).
- **Adversarial cross-family pass** — used here as the umbrella for the two cross-family roles
  from `review-convergence`: code-review's **refuter** (precision) and spec-review's **UNION
  second opinion** (recall). Descriptive, not a coined entity — no glossary row.

## US-1 — A neutral effort/model passthrough on the fresh-session spawn

- AC-1.1 `spawn-fresh-session.sh` SHALL accept `--effort <level>` and `--model <name>`.
- AC-1.2 WHEN the active harness is `claude`, THE spawn SHALL map them to `--effort <level>`
  and `--model <name>`.
- AC-1.3 WHEN the active harness is `codex`, THE spawn SHALL map them to
  `-c model_reasoning_effort=<level>` and `-m <name>`.
- AC-1.4 WHEN neither flag is given, THE spawn SHALL launch with the harness default
  (behavior unchanged).
- AC-1.5 WHEN the active harness has no effort/model mapping (e.g. `pi`) AND a flag is given,
  THE spawn SHALL omit the flags and warn that effort/model is unsupported for that harness —
  not silently drop them (consistent with AC-4.4).

## US-2 — The review wrappers thread per-role effort

- AC-2.1 `spawn-code-reviewer.sh` and `spawn-spec-reviewer.sh` SHALL accept `--effort`/`--model`
  and apply them to the primary review spawn.
- AC-2.2 `cross-family-review.sh` SHALL accept a **separate** effort/model for the cross-family
  spawn, so the adversarial pass can run at a higher tier than the primary. Code-review's
  refuter and spec-review's UNION second opinion consume it once `review-convergence` routes
  them through this helper (T9b/T10).
- AC-2.3 WHEN a role's effort/model is unset, THAT role SHALL inherit the harness default
  (no behavior change).

## US-3 — Differential effort must earn its cost

- AC-3.1 AN eval SHALL measure whether a higher effort on the adversarial cross-family pass
  lifts its reliability (refuter precision / second-opinion recall) versus the default tier,
  on the existing cross-family A/B fixture.
- AC-3.2 A higher-effort default for the adversarial pass SHALL ship only if the eval shows a
  reliability gain; otherwise the default stays the base tier (cost discipline). (When adopted,
  it lives at the user-facing wrapper — AC-4.2.)

## US-4 — Default at the top layer; explicit, compatible config

- AC-4.1 `spawn-fresh-session.sh` and `cross-family-review.sh` SHALL NOT inject an effort/model
  default — they pass an explicit value through or omit the flag, so no default is buried in a
  lower layer.
- AC-4.2 ANY Foundry-chosen default (e.g. an A/B-gated adversary tier) SHALL be set at the
  user-facing review wrapper, where the user can override it with an explicit flag.
- AC-4.3 THE effort/model SHALL be passed as explicit CLI flags/arguments through the call
  chain, adding no new environment variable to the config surface.
- AC-4.4 Foundry SHALL forward the effort level verbatim and SHALL NOT silently rewrite it.
- AC-4.5 A Foundry-chosen default (AC-4.2) SHALL be a level valid for the active harness — the
  adversary runs at the intended tier, never a silent fallback to base. (The T0 tracer found
  claude warns and falls back to its default on an unknown level rather than erroring, so a
  Foundry default must be harness-valid.)
- AC-4.6 `--effort`, `--model`, and the existing `--harness` SHALL compose without conflict —
  orthogonal axes (reasoning, model, harness family).

## Metrics

- The neutral knob maps to the right per-harness flag (`claude --effort` vs `codex -c
  model_reasoning_effort=`) — asserted by a dry-run test, no LLM.
- Differential effort on the adversarial pass lifts recall/precision without a
  disproportionate cost — measured by the eval (AC-3.1).
- No buried defaults, no new env var: the dry-run asserts the bare command is unchanged when no
  flag is given, and config flows as explicit flags through the call chain (AC-4.1, 4.3).
