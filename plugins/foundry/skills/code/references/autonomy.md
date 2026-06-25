# Lifecycle autonomy — the dial

How far the `code` lifecycle runs before it hands back. Set it once at Frame; read it —
never re-ask — on every later stage and loop iteration.

## Set or read the directive (Frame)

Resolve the directive in this precedence, stopping at the first that applies:

1. **Run-state** — `.foundry/tmp/lifecycle-run.json`, if a prior iteration wrote it.
2. **Supplied** — a `/loop` prompt or a Codex `/goal` that names the scope (see Harness).
3. **Ask** — through the harness's question tool: the **level** and the **stop-point**.
4. **Default** — no question tool and nothing supplied → **Supervised / this feature**;
   say so before proceeding.

Then record it, so it survives a context reset or a loop iteration:

```json
{ "level": "guided",
  "stopPoint": { "kind": "card", "id": "<card>" },
  "completed": [],
  "startedAt": "<iso8601>" }
```

`level` ∈ `supervised | guided | autonomous`. `stopPoint.kind` ∈
`feature | card | epic | roadmap` (`id` only for `card`). Manage this file directly —
rewrite the whole object; never leave it half-edited.

## The levels

The level decides who resolves a **soft fork** — a judgment call with more than one
defensible answer (an ambiguous AC you can reasonably interpret, a design tradeoff, a
blocking review finding with several fixes). A **hard blocker** — a gate that will not
pass after its retry budget, a missing dependency, or an ambiguity with no defensible
resolution — halts every level.

| Level | Soft fork | Unambiguous Design gate | Commit | Hands back |
|---|---|---|---|---|
| Supervised | ask you | ask you | ask you | after one feature |
| Guided | **ask you** | self-approve | feature branch | at the stop-point |
| Autonomous | **decide + record** | self-approve | feature branch | stop-point / hard blocker |

Supervised asks at gates; Guided asks at decisions; Autonomous asks at nothing but hard
blockers. **Invariant, every level:** never push or merge to the default branch without an
explicit go-ahead. Higher autonomy widens soft-fork latitude, never that floor.

A soft fork Autonomous decides is recorded — feature, the fork, the option chosen, why —
for the stop-point summary.

## The continuation loop (after Finish)

When a feature reaches Finish, append it to `completed` and check the stop-point:

| stop-point | reached when |
|---|---|
| `feature` | the feature just finished (Supervised is always this) |
| `card <id>` | the named card is Done |
| `epic` | every card under the current epic is Done |
| `roadmap` | no eligible card remains |

- Reached, roadmap exhausted, or a hard blocker → **stop** and emit the run summary.
- Not reached and level ≥ Guided → claim the next eligible ROADMAP card and re-enter Frame.

## The run summary (handback)

On stop, report: features finished and each gate PASS; soft forks decided without asking
(Autonomous); where it stopped and why. Under `/loop`, state **"stop-point reached"** so
the loop stops re-arming.

## Harness integration

| Harness | Scope | Gate behavior |
|---|---|---|
| Claude Code `/loop` | loop prompt / run-state; stop-point = when to stop re-arming | the recorded level |
| Codex `/goal` | the goal's terminal milestone = the stop-point | approval mode → level (Read-only → Supervised, Auto → Guided, Full Access → Autonomous) |
| interactive | the Frame question | the recorded level |

Read the directive once; never re-ask on a later stage or iteration.
