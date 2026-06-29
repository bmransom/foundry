> **Status:** Planned (2026-06-29) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — verify-by-execution

## Summary

Make a code-review finding **proven**, not merely plausible. Today the reviewer and the
cross-family refuter verify by *reading* — a runtime claim is a hypothesis confirmed by re-reading,
which is exactly where confident-but-wrong "false feedback" survives. This feature gives the
**adversary an executor**: for a finding that makes a **checkable** claim — a failing test, a wrong
runtime value, a reproducible fault — the refuter **runs** the check (the finding's existing test, a
minimal repro snippet, or `lldb` via the `debug` skill for a native fault) and **keeps only what
reproduces, drops what does not**. A finding that cannot be cheaply executed is stamped a
**hypothesis** (advisory). The rule that matters: **a blocking finding must be proven to block —
don't let an unverified executable claim fail a PR.** This subsumes `refuter-reproduce` as the
native/`lldb` executor.

## Glossary impact

- **Verified finding** — a finding an executor **ran and reproduced**; it may block. Prior art:
  test-driven verification / proof-by-reproduction. Provenance recorded in `knowledge/glossary.md`.
- **Hypothesis finding** — a finding inferred by reading but **not** reproduced by execution (the
  claim is non-executable, or too expensive to run cheaply); advisory only, never blocking. Prior
  art: the scientific hypothesis (unproven until tested) / a property test's "hypothesis".
- **Executor** — how a checkable finding is run: its **existing test**, a **repro snippet**, or
  **`lldb`** (the `debug` skill) for a native runtime fault. Prior art: the Strategy "executor"
  role / a test runner — one component that runs a check behind a single contract.

## US-1 — Findings carry a verification status

- AC-1.1 Each finding SHALL be one of **verified** (an executor ran and reproduced it),
  **refuted** (an executor ran and it did not reproduce), or **hypothesis** (not executed).
- AC-1.2 WHEN a finding is **refuted**, it SHALL be dropped from the verdict.
- AC-1.3 WHEN execution is **active** and a blocking executable finding **could not be run** by any
  executor (it stays a hypothesis, AC-3.2 — distinct from refuted, which ran and disproved), it
  SHALL be demoted to advisory — it SHALL NOT fail the verdict.
- AC-1.4 A finding whose claim is **non-executable** (naming, structure, docs-sync, an unimplemented
  AC, taste) SHALL keep its existing evidence-based verification — out of scope for execution, not
  demoted.
- AC-1.5 WHEN execution is **not active** (single-harness — no refuter, AC-2.3), findings SHALL keep
  their existing read-based verification and blocking status; verify-by-execution is a **no-op** and
  SHALL NOT demote a finding for lack of execution (no recall regression versus today's reviewer).

## US-2 — The refuter executes the check (DROP-only preserved)

- AC-2.1 THE cross-family refuter SHALL, per checkable finding, select an executor and run it,
  recording verified / refuted for that finding.
- AC-2.2 Execution SHALL be **DROP-only**: it may drop (refuted) or demote (unverified-executable)
  a finding, never ADD one — recall-monotone-down, precision-up, preserving the single asymmetric
  refuter pass (not a debate).
- AC-2.3 WHEN the repo is single-harness (no complementary family), the refuter and the execution
  layer are skipped, as today — the reviewer runs single-agent with its existing read-based blocking
  (AC-1.5), not the verify-by-execution path.

## US-3 — Scope by severity and cost

- AC-3.1 Verification SHALL target **blocking / high-severity** findings; an advisory nit SHALL NOT
  trigger an executor.
- AC-3.2 WHEN a finding's check is not **cheaply** runnable (no runnable target, an expensive
  build, no repro), it SHALL stay a **hypothesis** rather than block the run — execution is
  best-effort, never a hang.

## US-4 — The native executor (folds refuter-reproduce)

- AC-4.1 WHEN a checkable finding is a runtime fault in a **buildable native target**
  (C/C++/Rust/Swift), THE executor SHALL invoke the `debug` skill: build with symbols, set a
  breakpoint at the claimed site, run, and confirm the bad state — reproduce → verified, else
  refuted (proof-by-reproduction).
- AC-4.2 THE native executor SHALL be opt-in and native-only; a non-native finding uses the
  test/snippet executor instead.

## US-5 — Eval (deterministic; live deferred)

- AC-5.1 A hermetic test (a mock executor seam) SHALL prove: a finding whose executor **reproduces**
  is kept and marked verified; one that **does not reproduce** is dropped; a **non-executable**
  finding stays a hypothesis; a blocking executable finding left **unverified** is demoted to
  advisory (does not fail the verdict). The live `lldb` / test run ships deferred.

## Metrics

- A non-reproducing blocking finding never fails the verdict (dropped or demoted); a reproducing
  finding is kept and labeled **verified** — asserted by the mock-executor test.
- Execution is best-effort: an unrunnable check yields a hypothesis, never a hang or a hard error.
- **Additive, no recall regression:** with execution active, precision rises (refuted dropped,
  un-runnable executable blocking demoted); with execution off (single-harness) the verdict matches
  today's reviewer exactly. A confidently-read but un-runnable executable claim no longer blocks
  *under active execution* — the deliberate "proven, not plausible" trade — but does still block in
  the single-harness no-op path.
