> **Status:** Done (2026-06-29) — built; live lldb/test run deferred. Tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — verify-by-execution

## Decisions

- **The adversary is the executor's home — not a new agent.** The cross-family refuter already
  gates "is this finding real?" with a DROP-only pass. Execution is simply a **stronger DROP
  criterion than reading**: where the refuter today keeps a finding on read-evidence, it now *runs*
  the check. Reusing the refuter keeps one fresh-context, context-isolated, single-asymmetric pass;
  a separate "verifier agent" would duplicate the spawn and the isolation discipline for no gain.
- **DROP-only is preserved — execution removes or demotes, never adds.** A refuted finding is
  dropped; an executable blocking finding left unverified is demoted to advisory. Neither can add a
  finding, so recall is still monotone-down and the pass stays asymmetric (not a debate). This is
  the same invariant the existing refuter holds, extended from "drop" to "drop **or** demote".
- **Three executors behind one contract (Strategy).** A checkable finding routes to its **existing
  test**, a **repro snippet**, or **`lldb`** (the `debug` skill) by claim type + language. The
  native/`lldb` executor *is* `refuter-reproduce` — folded in here rather than specced apart, so the
  umbrella and its instance share one design (avoiding the wrong-abstraction split of an umbrella
  from its only-named instance). Each executor returns `verified | refuted | unrunnable`.
- **"Hypothesis" is the honest label for the un-run.** A read-only inference is not pretended to be
  proven; an un-executable or too-expensive claim is stamped **hypothesis** (advisory). A
  **blocking** finding must be **verified** (or a mechanically-checked class — an unimplemented AC
  via the matrix, docs-sync via `knowledge.py` — which are already verified by mechanism). This is
  the rule "don't let an unverified claim block a PR," made structural. **Additive, not a
  regression:** the gating fires only when execution is **active** (multi-harness, refuter on). In a
  single-harness repo the execution layer is off, so the reviewer keeps today's read-based blocking
  — verify-by-execution is a **no-op** there and never demotes a finding for lack of an executor
  (AC-1.5). It can only raise precision where it runs; it never lowers recall where it does not.
- **Best-effort, cost-scoped.** Only blocking/high-severity findings trigger an executor, and only
  when the check is **cheaply** runnable; otherwise the finding stays a hypothesis. Execution never
  hangs the review — an unrunnable target degrades to hypothesis, it does not error.

## Mechanism

```mermaid
flowchart TD
  ref[refuter: candidate FLAGGED findings] --> sev{blocking + checkable?}
  sev -- no --> hyp[mark hypothesis (advisory)]
  sev -- yes --> pick{executor by claim/lang}
  pick -- has a test --> t[run the finding's test]
  pick -- value/path claim --> s[run a repro snippet]
  pick -- native fault --> l[lldb via debug skill]
  t & s & l --> res{reproduced?}
  res -- yes --> ver[verified — may block]
  res -- no --> ref2[refuted — DROP]
  res -- unrunnable --> hyp
```

| Surface | Change |
|---|---|
| `plugins/foundry/scripts/verify-finding.sh` | New: given a finding (claim, `file:line`, suggested check) + a language/target, select an executor and run it via a `VERIFY_EXEC_CMD` seam (default: the real executor); return `verified \| refuted \| unrunnable`. Reuses the `cross-family-review.sh` / `spawn-fresh-session.sh` spawn pattern for the `lldb` executor (the `debug` skill). |
| `plugins/foundry/skills/code-review/SKILL.md` + `references/dimensions.md` | The refuter section gains the verify-by-execution rule: per blocking checkable finding, run an executor; **verified** may block, **refuted** drops, **hypothesis** (un-run) is advisory. Keep `SKILL.md` ≤120. |
| `plugins/foundry/skills/code-review/references/convergence.md` | The verdict honors the labels: a blocking finding blocks only if **verified** or mechanically-checked. |
| `tests/verify_finding_test.sh` | Hermetic: a mock `VERIFY_EXEC_CMD` returns reproduces / not / unrunnable — assert keep+verified, drop, hypothesis, and that an unverified blocking executable finding is demoted (AC-5.1). |
| `knowledge/glossary.md` | `Verified finding`, `Hypothesis finding`, `Executor`. |

## Metrics

Discrimination, not green-ness: the mock-executor test asserts reproduce→keep+verified,
not-reproduce→drop, unrunnable→hypothesis, and unverified-blocking→demoted. The `lldb` executor's
live run is deferred (like the `debug` skill's live eval), so the gate stays hermetic.

## Out of scope

- A symmetric agent debate (rejected — DROP-only single pass preserved).
- Running an executor for advisory nits or non-executable judgment findings (cost; AC-1.4, AC-3.1).
- Auto-constructing a repro for an arbitrarily complex finding — the snippet executor handles
  cheap, local repros; a deep repro stays a hypothesis (AC-3.2).
