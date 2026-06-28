> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — reviewer-effort

## Wave 0 — tracer bullet (de-risk the flag syntax before building)

- T0 (**done**) Tracer: confirm the CLIs accept the flags. Result — `claude --effort high`
  parses (valid: `low/medium/high/xhigh/max`); `codex -c model_reasoning_effort=high` parses.
  **Finding that changed the design:** an unknown `claude --effort` value is **not** an error —
  claude *warns and falls back to its default effort* (`rc=0`). So the old "unknown → launch
  error" claim (the *Level strings pass through* decision) was wrong: AC-4.4 keeps the
  no-silent-rewrite guarantee and AC-4.5 adds "a Foundry-set default must be a harness-valid
  level" (no silent base-tier fallback).

## Wave 1 — the neutral passthrough

- T1 `plugins/foundry/scripts/spawn-fresh-session.sh`: parse `--effort <level>` / `--model
  <name>`; in the `claude` builder append `--effort <level> --model <name>`, in the `codex`
  builder append `-c model_reasoning_effort=<level> -m <name>`; forward verbatim and omit when
  unset — no default injected here. For a harness with no mapping (`pi`), omit the flags and
  warn "unsupported" rather than silently dropping them (AC-1.1–1.5, AC-4.1, AC-4.4).
- T2 A dry-run test (`tests/`): `--effort high` → `claude --effort high` under
  `AGENT_HARNESS=claude` and `codex -c model_reasoning_effort=high` under `AGENT_HARNESS=codex`;
  unset → bare command unchanged (the mapping AC-1.2–1.4; no buried default, no new env var —
  config flows as flags: AC-4.1, AC-4.3). Hermetic (`AGENT_TMUX=/bin/echo`, no LLM).
- Gate: the dry-run test + `fresh_session_test` pass.

## Wave 2 — per-role effort in the review wrappers

- T3 `plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh`: accept
  `--effort`/`--model` for the primary review spawn (AC-2.1); scope the flag to the reviewer
  spawn, **not** the shared `runner_args` (which also feeds the inline refuter, which must stay
  at base tier). Default unset → harness default (AC-2.3). A wrapper dry-run asserts
  `--harness <fam> --effort high --model <m>` composes — the mapped effort and model flags land
  on the chosen family with no conflict (AC-4.6).
- T4 `plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh`: accept
  `--effort`/`--model` for its primary spawn (AC-2.1). `plugins/foundry/scripts/cross-family-review.sh`:
  accept + forward a **separate** effort/model to the cross-family spawn (AC-2.2) — consumed by
  code-review's refuter and spec-review's UNION once they adopt the helper (`review-convergence`
  T9b/T10). It forwards an explicit value or omits the flag — no default injected (AC-2.3, AC-4.1).
- Gate: `code_review_cycle_test` + `cross_family_review_test` pass; defaults unchanged.

## Wave 3 — the A/B + knowledge

- T5 `evals/harness/` cross-family A/B: a base-vs-higher-effort arm on the cross-family fixture
  — does dialing up the adversary lift precision (refuter) / recall (UNION) at acceptable cost
  (AC-3.1)? The higher-effort default ships only on a proven gain (AC-3.2), set at the
  user-facing wrapper (AC-4.2) as a harness-valid level (AC-4.5). It reaches
  code-review's refuter and spec-review's UNION only after `review-convergence` T9b/T10 route
  them through `cross-family-review.sh`.
- T6 `knowledge/log.md`: record the effort/model passthrough and the A/B outcome.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; the A/B arm runs and records a result.
