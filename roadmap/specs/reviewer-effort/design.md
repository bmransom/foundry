> **Status:** Planned (2026-06-28) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — reviewer-effort

## Decisions

- **Neutral knob + per-harness map — the existing harness-agnostic pattern.** Foundry exposes
  `--effort <level>` / `--model <name>`; `spawn-fresh-session.sh`'s per-harness command builder
  maps them to each CLI's real flag — `claude --effort <level> --model <name>` vs
  `codex -c model_reasoning_effort=<level> -m <name>` (both confirmed in `--help`). This is the
  same place that already maps `--dangerously-skip-permissions`, so no new abstraction — one
  more row in the same switch.
- **Differential effort: spend it on the adversary.** The value is the *cross-family* pass —
  the refuter (precision) and the spec-review UNION second opinion (recall) are where a missed
  or wrongly-kept finding costs most, and where the hypothesis (eval-gated, US-3) is that extra
  reasoning pays off. The primary review can stay the base tier; the wrappers carry a **separate** role
  effort/model so only the adversary is dialed up.
- **Eval-gated default, like the refuter.** A higher-effort default ships only after an A/B
  proves a reliability gain — mirroring `review-convergence`'s "ships disabled until the A/B is
  green" discipline. Until then the knob exists but defaults to the harness base tier (zero cost
  change).
- **Level strings pass through; no Foundry taxonomy.** Foundry forwards the level verbatim and
  coins no enum of its own (claude: `low/medium/high/xhigh/max`; codex differs). The harness
  handles an unknown level its own way — the **T0 tracer found claude warns and falls back to
  its default effort** (not a hard error), so Foundry must ensure any default *it* sets (AC-4.2)
  is a harness-valid level, else the adversary silently runs at base tier. (Foundry does not
  validate user-supplied levels — claude's own warning covers a user typo.)
- **Default at the top layer — never bury it.** `spawn-fresh-session.sh` and
  `cross-family-review.sh` inject no default — they pass an explicit value through or omit the
  flag. Any Foundry-chosen default (e.g. the A/B-gated adversary tier) lives at the user-facing
  review wrapper, where the user could instead pass an explicit value. A default is always set
  where a value could be given, never silently deep in the call chain.
- **Config as explicit flags, not environment variables.** Effort/model flow as CLI
  flags/arguments through the call chain — no new env var. (The existing `AGENT_HARNESS` /
  `*_SPAWN_CMD` env vars are harness detection + test seams, not feature config; reviewer-effort
  does not extend that surface.)
- **No bounded-context map / class diagram — deliberately.** This is a config passthrough: one
  small interface (the per-harness flag map in `agent_command()`), no solver routine, no
  algorithm, no internal data structure to abstract, no hot path. A bounded-context/class
  diagram or a performance pass would be pattern cosplay over a flag map — declined per the
  simplicity rule. The flow diagram below is the whole architecture; the only compatibility
  surfaces are the harness-specific level vocabulary (AC-4.4) and the orthogonal
  `--effort`/`--model`/`--harness` axes (AC-4.6).

## Mechanism

```mermaid
flowchart LR
  flag["--effort high / --model X"] --> builder[spawn-fresh-session per-harness builder]
  builder -->|claude| c["claude --effort high --model X"]
  builder -->|codex| x["codex -c model_reasoning_effort=high -m X"]
  wrap[review wrappers] -->|primary role| builder
  wrap -->|adversary role: separate effort| builder
```

| Surface | Change |
|---|---|
| `plugins/foundry/scripts/spawn-fresh-session.sh` | Parse `--effort`/`--model`; in the `claude`/`codex` command builders, append the mapped flags (default: omit → harness default). A harness with no mapping (`pi`) omits the flags and warns "unsupported" rather than dropping silently (AC-1.5). |
| `plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh` | Accept `--effort`/`--model` for the primary review spawn. (The refuter's separate effort arrives via `cross-family-review.sh` once code-review adopts the helper — `review-convergence` T9b.) |
| `plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh` | Accept `--effort`/`--model` for its primary review spawn. |
| `plugins/foundry/scripts/cross-family-review.sh` | Accept + forward a separate effort/model to the cross-family spawn (the adversary role). |
| `evals/harness/` cross-family A/B | Add a base-vs-higher-effort arm: does dialing up the adversary lift precision/recall, at what cost? |
| `knowledge/log.md` | Record the effort/model passthrough. |

## Metrics

Discrimination, not green-ness: a dry-run test asserts `--effort high` becomes `claude --effort
high` under `AGENT_HARNESS=claude` and `codex -c model_reasoning_effort=high` under
`AGENT_HARNESS=codex`, and that omitting the flag leaves the bare command unchanged. The A/B
eval measures the adversary's reliability at base vs higher effort on the cross-family fixture;
the higher tier becomes the default only on a proven gain. Runtime: flag mapping is a one-shot
string build — perf N/A.

## Out of scope

- Per-dimension or per-finding effort; auto-tuning effort by spec size.
- Cost budgeting (the harnesses expose budget flags) — a separate concern.
- A Foundry-defined effort taxonomy — levels pass through to the harness.
