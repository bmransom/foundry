> **Status:** Done (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# gate-feedback — requirements

The driver retries a failed stage with a byte-identical prompt: no gate output, no
attempt number, no explanation reaches the next attempt. The first production run
(`r-20260703023624-22b6`) paid three opus build attempts ($29.83 → $19.63 → $8.30) that
died on the same miss — the single actionable string (`knowledge/index.md is stale`) was
printed to the driver's log and shown to no agent. Review→build loop-back is blind the
same way, with a 20-round ceiling. The ledger also drops each stage's returned text, so
the failure could not even be diagnosed post-hoc.

## US-1 Retries carry the failure

As the driver, I want a failed gate's evidence in the next attempt's prompt, so a retry
is a correction, not a blind replay.

- AC-1.1 WHEN a judgment or mixed stage's gate FAILs and the retry cap is not reached,
  THE SYSTEM SHALL invoke the next attempt with feedback carrying the failed gate's
  name, the 1-based number of the attempt that failed, and the failure detail.
- AC-1.2 WHEN a stage runs its first attempt, THE SYSTEM SHALL compile the prompt with
  no feedback section — byte-identical to the pre-feature prompt for the same inputs.
- AC-1.3 WHEN the review stage FAILs and the run loops back to build, THE SYSTEM SHALL
  pass the review output's tail as the build attempt's feedback.

## US-2 Gates yield evidence

As a gate author, I want a FAIL to explain itself, so feedback has content.

- AC-2.1 WHEN a command gate FAILs, THE SYSTEM SHALL set the outcome's detail to the
  command's captured output tail (capped) while still writing the full output to the
  driver's stdout.
- AC-2.2 WHEN a marker gate FAILs, THE SYSTEM SHALL set the detail to the marker name
  and the value seen, or state that no marker line was found.
- AC-2.3 WHEN the plan gate FAILs, THE SYSTEM SHALL set the detail to the path it
  required and did not find, or to the absence of a Spec cell when the card has none.

## US-3 The ledger keeps the agent's word

As a maintainer diagnosing a halted run, I want each attempt's returned text persisted,
so I can read what the agent believed it did.

- AC-3.1 WHEN a gate is evaluated for a stage that returned text, THE SYSTEM SHALL
  record a capped tail of that text on the `gate_evaluated` event as `result_text`.
- AC-3.2 WHEN reading an events file written before this change, THE SYSTEM SHALL parse
  it unchanged (`result_text` defaults to null).

## US-4 The build rubric closes the loop

As a build-stage agent, I want the rubric to tell me to run the repo's test command
before finishing, so I never exit believing untested work is green.

- AC-4.1 WHEN the build rubric is compiled into a stage prompt, THE SYSTEM SHALL
  include the instruction to run the repo's test command (`[gate].test`) and finish
  only when it exits 0; the rubric SHALL still pass the orchestration-verb validator.
