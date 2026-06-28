> **Status:** Draft (2026-06-25) — pending approval.
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — lifecycle autonomy

## Where it lives

The dial is an addition to the `code` skill's **Frame stage (0)** plus a **continuation
loop** after Finish (7). No new top-level skill; the lifecycle stays the dispatcher.

## The dial

One **autonomy level** with a **stop-point** parameter. The distinguishing axis is the
**soft fork** — a judgment call with more than one defensible answer (an ambiguous AC, a
design tradeoff, a blocking review finding with several fixes) — as opposed to a **hard
blocker** the agent cannot proceed past. A hard blocker halts every level (AC-3.4); the
level decides who resolves a soft fork:

| Level | Soft fork | Unambiguous gate | Commit | Hands back |
|---|---|---|---|---|
| **Supervised** | asks you | asks you | asks you | after one feature |
| **Guided** | **asks you** | self-approves | feature branch | at the stop-point |
| **Autonomous** | **decides + records rationale** | self-approves | feature branch | stop-point or hard blocker |

The spectrum: Supervised asks at *gates* → Guided asks at *decisions* → Autonomous asks
at *nothing but hard blockers*.

The **never push/merge to the default branch without a go-ahead** boundary is invariant
across levels — the safety floor (AC-2.4). Higher autonomy widens *soft-fork latitude*,
never the irreversible-action floor.

## Run-state

`.foundry/tmp/lifecycle-run.json` (gitignored) carries the directive across context
resets and loop iterations:

```json
{ "level": "guided",
  "stopPoint": { "kind": "card", "id": "turn-based-loop" },
  "completed": ["deck-and-cards", "hand-evaluation"],
  "startedAt": "<iso8601>" }
```

Directive precedence (AC-1.3): run-state file → a directive named in the invoking prompt
(`/loop` / `/goal`) → an interactive ask → the Supervised / this-feature default.

## The continuation loop

After Finish (stage 7), the skill consults run-state:

- stop-point reached, roadmap exhausted, or a hard blocker → stop; emit the run summary.
- else, level ≥ Guided → append the finished feature to `completed`, claim the next
  eligible ROADMAP card, and re-enter Frame for it.
- level = Supervised → always stop after one feature.

## Stop-point resolution

| kind | reached when |
|---|---|
| `feature` | the current feature reaches Finish |
| `card <id>` | the named card is Done |
| `epic` | every card under the current epic is Done |
| `roadmap` | no eligible card remains |

## Harness integration

| Harness | Scope directive | Gate behavior |
|---|---|---|
| Claude Code `/loop` | the loop prompt / run-state | the recorded level |
| Codex `/goal` | the goal's terminal milestone | the Codex approval mode (Read-only / Auto / Full) |
| interactive | the Frame question | the recorded level |

Under `/loop`, the run summary names "stop-point reached" so the loop stops re-arming
(AC-4.3). Under `/goal`, the agent maps the Codex approval mode to a level — Read-only →
Supervised, Auto → Guided, Full Access → Autonomous — rather than re-asking (AC-4.2).
The directive is read once and persisted; no iteration re-prompts (AC-1.3).

## A hard blocker vs a soft fork

A **hard blocker** — a gate that will not pass after the lifecycle's own retry budget
(e.g., code-review blocking findings persisting past three rounds), a missing dependency,
or an ambiguity with no defensible resolution — halts the run at **every** level and hands
back with the specific blocker (AC-3.4). Autonomy never papers over a hard blocker.

A **soft fork** — a judgment call the agent *can* resolve defensibly — is the dial's
dividing line: **Guided** stops and asks you; **Autonomous** picks the most defensible
option and records the rationale for the stop-point summary. The same fork, two behaviors;
that is the whole difference between the two upper levels.

## Metrics

See requirements §Metrics — honored stop-point, no runaway push/merge, no re-ask. The
eval (T6) measures all three against a fixture.
