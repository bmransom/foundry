> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# interactive-skills — requirements

The v2 rebuild (#70) deleted the `code`, `handoff`, `spec-review`, `code-review`, and
`knowledge` skills and replaced the lifecycle ones with the headless driver. That erased the
**interactive** workflow — the maintainer codes from Claude Code / Codex sessions and used
"tell the agent to use the code skill" to walk a card in-context. The intent was to refine
that workflow, not remove it. Restore the interactive wrappers, coexisting with the driver.

## US-1 The interactive lifecycle is invocable again

As a maintainer in a session, I want to name a skill that walks the current agent through
the lifecycle, sharing the conversation, so I pair on a card instead of firing off the driver.

- AC-1.1 THE `code` skill SHALL walk the ordered lifecycle stages, gating between them, in
  the current session.
- AC-1.2 THE `code` skill SHALL name `.foundry/bin/foundry run <card-id>` as the autonomous
  alternative and state it makes no determinism claim of its own.

## US-2 Stage skills single-source their judgment

As a maintainer, I want the stage skills to grade by the same rubrics the driver uses, so the
interactive and headless paths never drift.

- AC-2.1 THE `spec-review`, `code-review`, and `knowledge` skills SHALL fetch their judgment
  from `.foundry/bin/foundry rubric <stage>` rather than embedding it.
- AC-2.2 WHEN `foundry rubric` runs with no argument, THE SYSTEM SHALL print the ordered
  stage map (stage · kind · gate) from the lifecycle graph.
- AC-2.3 WHEN `foundry rubric <stage>` names a stage with a rubric, THE SYSTEM SHALL print
  that rubric byte-identical to what the driver compiles.
- AC-2.4 WHEN `foundry rubric <stage>` names a mechanical stage, THE SYSTEM SHALL say it has
  no rubric and name its gate; an unknown stage SHALL fail listing the valid stages.

## US-3 Handoff is restored whole

As a maintainer at a milestone, I want the handoff workflow back, so a fresh session
continues with durable, verified state.

- AC-3.1 THE `handoff` skill SHALL write `.agent/handoff/HANDOFF.md` in the briefing shape
  and spawn a same-harness successor via the surviving fresh-session runner.

## US-4 Shipped with eval cases

- AC-4.1 EACH restored skill SHALL carry a triggering eval case, and the plugin/skill
  validators (context budget, references, manifest) SHALL pass.
