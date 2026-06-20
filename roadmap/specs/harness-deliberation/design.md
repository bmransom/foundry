> **Status:** In progress (2026-06-19) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — harness deliberation

## Architecture overview

Harness deliberation is a Foundry skill that starts a mediated design session
between exactly two harnesses: Codex and Claude Code. The broker runs the
harnesses in non-interactive turns, records immutable prompt and final message
payloads, renders a tmux view for the mediator, and generates a Foundry spec
after the mediator closes all questions.

The design separates protocol from view:

- **Protocol**: append-only events, immutable payloads, deterministic state, and
  gated spec generation.
- **View**: tmux panes for participant status, latest final messages,
  `transcript.md`, `state.md`, and a mediator command shell.

The tmux view is replaceable Tier 3 output. It is not the evidence of record.

## Relationship to spec-review

Harness deliberation does not replace or merge with `spec-review`.
Deliberation creates and shapes a spec through multiple participant turns.
`spec-review` remains the downstream gate that reviews the generated
requirements, design, and tasks before approval.

Participant prompts include the repo contract that `spec-review` enforces:
canonical vocabulary, writing style, spec format, feature-file conventions, gate
commands, and architecture concept paths. This gives each turn the same contract
inputs without running `spec-review` inside every exchange.

## Components

| Component | Location | Purpose |
|---|---|---|
| Skill entrypoint | `plugins/foundry/skills/harness-deliberation/SKILL.md` | Explains when to use the capability and delegates to the runner. |
| Runner wrapper | `plugins/foundry/skills/harness-deliberation/scripts/spawn-deliberation.sh` | Starts preflight, creates the session, and opens tmux. |
| Harness availability helper | `plugins/foundry/scripts/harness-status.py` | Returns a harness availability result for each selected harness by probing command presence, auth, reachability, and bounded live turns during bootstrap verify, `/foundry:update`, and deliberation. |
| Broker | `plugins/foundry/scripts/harness-deliberation-broker.py` | Owns session storage, turn execution, mediator commands, rebuild, snapshots, and spec generation. |
| Eval fixtures | `evals/fixtures/harness-deliberation/` | Static participant outputs, corrupted payloads, contradiction cases, and snapshot reconstruction cases. |
| Eval driver | `evals/harness/harness-deliberation-eval.sh` plus tests | Proves storage, replay, snapshot, contradiction, stall, and live smoke behavior. |

The broker owns session operations and hides IO details from the skill.
Codex and Claude Code adapters construct commands and capture output because the
harnesses use different flags and output formats.

## Harness availability

The manifest records repo intent. Harness availability records whether the
current machine and user account can run those harnesses now. Foundry keeps those
separate because a local subscription, auth, or quota failure does not prove the
repo no longer targets that harness.

`harness-status.py` is the shared checker for bootstrap verify,
`/foundry:update`, and the deliberation broker. The script name uses **status**
for the stored availability result object; the glossary binds it to **Harness
availability**. It reads `.foundry/manifest.json` `harnesses`, runs each selected
harness adapter with a timeout, redacts account identifiers from raw output, and
writes transient availability results under `.foundry/tmp/harness-status/`. The
manifest is never edited by an availability check.

The v1 harness availability results are:

| Result | Meaning | Default handling |
|---|---|---|
| `ok` | Command, auth, reachability, and bounded live-turn probe passed. | Continue. |
| `missing-command` | The selected harness CLI is not installed or not on `PATH`. | Ask user to install it or remove the harness. |
| `not-authenticated` | The CLI reports no usable auth. | Ask user to log in or remove the harness. |
| `subscription-unavailable` | The CLI reports the account cannot use that harness or model. | Ask whether repo intent changed; offer `/foundry:update` remove flow. |
| `usage-limited` | A usage cap prevents new turns until reset, credit, or plan change. | Pause turns; preserve manifest by default. |
| `rate-limited` | A retryable rate limit prevents the current turn. | Pause and show retry timing when available. |
| `unknown-failure` | The adapter cannot classify the failure. | Stop and show redacted command output. |

Adapter probes are command-first and bounded:

- Codex: `codex login status`, `codex doctor --json`, then a live-turn probe
  when the next operation will spend Codex usage.
- Claude Code: `claude auth status` and a timeout-bounded
  `claude -p --output-format json --max-budget-usd 0.01 'Reply with OK.'`
  live-turn probe. `claude doctor` is not a required preflight probe because it
  can start unrelated checks.

`/foundry:update` owns harness toggles. When a user removes a harness,
`/foundry:update` changes only `.foundry/manifest.json` `harnesses` and that
harness's shim, such as `CLAUDE.md` for Claude Code. Shared files, including
`AGENTS.md`, stay in place. Removing the last harness is refused.

## Session layout

```text
.foundry/tmp/harness-deliberation/<session-id>/
  session.json
  events.jsonl
  state.json
  state.md
  transcript.md
  mediator.in
  turns/
    0001-codex/
      prompt.md
      final.md
      meta.json
      raw.log
    0002-claude/
      prompt.md
      final.md
      meta.json
      raw.json
  snapshots/
    0003-codex/
      snapshot.json
      tracked.diff
      untracked/
  raw/
    broker.log
  indexes/
    README.md
```

The store has three tiers:

| Tier | Files | Rule |
|---|---|---|
| Tier 1 | `events.jsonl` | Append-only canonical ledger. Corrections are new events. |
| Tier 2 | `prompt.md`, `final.md`, snapshots | Immutable payloads referenced by path and SHA-256. |
| Tier 3 | `state.json`, `state.md`, `transcript.md`, indexes | Rebuildable views from Tiers 1 and 2. |

`prompt.md` is a Tier 2 payload referenced by path and SHA-256, not embedded in
`events.jsonl`. Replay reads the exact prompt artifact while `events.jsonl`
stores event metadata rather than prompt bodies.

`raw.*` files are debug-only. They may differ by harness format, such as Codex
logs or Claude Code JSON, and do not participate in rebuild or spec generation.

## Event and state schema

Every event has `event_id`, `type`, `created_at`, `session_id`, and optional
`actor`, `round_id`, `turn_id`, `payloads`, and `supersedes` fields. Event IDs
are broker-assigned, monotonically increasing strings such as `e000001`.

The v1 event type set is closed:

| Event type | Purpose |
|---|---|
| `session_started` | Records repo root, base commit, participants, and session config. |
| `mediator_prompt` | Records the initial mediator prompt payload. |
| `repo_guidance` | Records prompt guidance paths, roles, required flags, existence, and content hashes. |
| `participant_final` | Records `prompt.md`, `final.md`, hashes, round ID, turn ID, and debug raw path. |
| `participant_failed` | Records prompt hash, exit status, and debug raw path. |
| `participant_limited` | Records usage-limit or rate-limit result, retry metadata when available, and the paused participant. |
| `question` | Opens or revises a mediator-accepted question. |
| `decision` | Applies `settled`, `rejected`, or `deferred-dissent` to a question. |
| `snapshot` | Records a portable scratch-worktree snapshot record. |
| `truncation` | Marks a snapshot incomplete because it exceeded the byte ceiling. |
| `stall` | Records that the configured no-progress threshold was reached. |

Questions are explicit state records. The broker does not infer required action
from participant prose. A participant can ask a question in `final.md`; it
becomes blocking only when the mediator records a `question` or `decision`
through `decide --file`.

`state.json` includes:

- `questions`: current question records keyed by `question_id`;
- `decisions`: effective decisions keyed by `decision_id`;
- `open_questions`: question IDs without an effective disposition;
- `deferred_dissent`: decision IDs with `deferred-dissent`;
- `snapshots`: complete and incomplete snapshot records;
- `rounds`: turn IDs grouped by round;
- `last_progress_hash`: hash of progress-bearing state.

Decision revisions use `supersedes` to point at the prior `decision_id`. The
latest valid event wins for effective state; older events stay in the ledger.

A progress hash excludes raw output, wall-clock fields, and pure turn metadata.
It includes effective questions, dispositions, deferred dissent, complete
snapshots, and generated-spec outline entries. `session.json` stores
`config.stall_rounds`, default `2`; that many consecutive rounds with unchanged
progress hash emits `stall`.

## Broker commands

The v1 command surface has six commands:

| Command | Purpose |
|---|---|
| `start --prompt <file> --session <id> [--attach]` | Create session storage, record the initial mediator prompt, run preflight, and open tmux. The runner materializes inline user prompts to a file before calling the broker. |
| `round` | Run one Codex turn and one Claude Code turn, alternating which participant runs first by round. |
| `decide --file <md-or-json>` | Record mediator decisions, revisions, and dispositions. |
| `rebuild` | Verify hashes and regenerate Tier 3 views from Tiers 1 and 2. |
| `spec --out roadmap/specs/<feature>` | Verify closure and generate `requirements.md`, `design.md`, and `tasks.md`. |
| `live-smoke --session <id> [--prompt <file>]` | Opt in to one real Codex plus Claude Code round, verify both `final.md` payloads, and fail if the consumer repo worktree changes. |

There is no v1 participant-count flag, compression flag, `/apply`, or
`/promote`.

## Data flow

**Start.** The skill writes the user's prompt to a mediator prompt payload, then
calls the runner. The runner invokes broker `start`, which checks `tmux`, `git
worktree`, `.foundry/manifest.json` for both selected harnesses, harness
availability through `harness-status.py`, and required repo guidance sources.
Preflight failures stop the session with exact failed checks.

**Round.** The broker renders compact state from `state.json` into the
participant prompt, adds the previous peer `final.md`, writes `prompt.md`, runs
the harness, captures `final.md`, records metadata and hashes, then appends
`participant_final`. A usage or rate limit appends `participant_limited`,
preserves the session, and waits for mediator action.
Participants read only compact state and peer-readable final messages unless the
mediator supplies named Tier 2 payloads.

Each rendered prompt starts with repo guidance:

- required `AGENTS.md` for standing rules, writing style, and gate commands;
- required `knowledge/glossary.md` for canonical domain language;
- required `roadmap/specs/README.md` for spec shape;
- required `roadmap/ROADMAP.md` for board state;
- optional `features/README.md` for executable feature-file conventions;
- optional `knowledge/validation.md` for gate inventory;
- optional active spec files and discovered `knowledge/**/*.md` files with
  `type: architecture` for architecture context.

The prompt includes guidance paths, roles, required flags, existence, and content
hashes. It does not inline guidance excerpts. Harnesses can read the files they
need with their own tools. The broker records a `repo_guidance` event so a later
review can see which repo contract shaped the turn.

**Decide.** The mediator records decisions with one disposition:

- `settled`: current decision feeds generated spec content.
- `rejected`: retained in history but omitted from generated spec content.
- `deferred-dissent`: non-blocking disagreement that must appear in `design.md`.

Decisions are revisable by new events that supersede old events. The ledger never
mutates.

**Rebuild.** `rebuild` verifies Tier 2 payload hashes, replays events, computes
the effective state, and regenerates `state.json`, `state.md`, and
`transcript.md`. It fails on missing payloads, hash mismatches, invalid
revisions, unknown dispositions, or nondeterministic Tier 3 output. Runtime
sessions compare regenerated Tier 3 views with the existing Tier 3 views.
Eval fixtures can store checked-in projections under `evals/fixtures/`.

**Spec.** `spec` first runs the same checks as `rebuild`. It refuses while
`open_questions` is nonempty. Successful spec generation writes
`roadmap/specs/<feature>/{requirements,design,tasks}.md` and includes
traceability for requirements and major design choices. It also reports that
per-turn guidance is not a final `spec-review` pass.

## Snapshot evidence

Snapshots are portable evidence from optional scratch worktrees. They do not
integrate patches.

Each snapshot records:

- base commit and scratch branch;
- tracked binary diff from `git diff --binary HEAD`;
- untracked files from `git ls-files --others --exclude-standard`;
- byte payloads for untracked files under `snapshots/<id>/untracked/`;
- hashes and byte counts;
- truncation status when a byte ceiling is exceeded.

Git object references are provenance, not storage. A valid snapshot must remain
inspectable after the scratch worktree is removed. Incomplete snapshots keep all
recorded hashes and metadata, but reconstruction is guaranteed only for captured
bytes.

## Tmux view

The v1 UI is a tmux session named `foundry-hd-<session-id>`. `start --attach`
attaches when stdout is an interactive terminal; otherwise it prints the exact
attach command.

Window `control` gives the mediator the whole session at a glance:

```text
codex pane       | claude-code pane
mediator command shell
```

The participant panes tail each participant's latest status and peer-readable
`final.md`; they do not show raw CLI streams by default. The mediator command
shell starts in the repo root with `FOUNDRY_HD_SESSION` set and prints the broker
command summary.

Window `state` tails `transcript.md` and `state.md` side by side. A web UI is
future Tier 3 work over the same event store.

## Error handling

| Failure | Handling |
|---|---|
| Missing `tmux`, `claude`, `codex`, or `git worktree` | `start` fails preflight with the command that failed. |
| Repo manifest missing one harness | `start` reports the required and present harness sets. |
| Manifest-selected harness unavailable | `start` reports the harness availability result and offers auth/subscription remediation or `/foundry:update` for changing the manifest harness set. |
| Harness usage or rate limit during a turn | Broker records `participant_limited`, pauses that participant, and waits for mediator action. |
| Required repo guidance source missing | `start` reports the missing path and refuses the session. |
| Harness command exits nonzero | Broker records `participant_failed`, keeps raw output, and waits for mediator action. |
| Payload hash mismatch | `rebuild` fails and names the path. |
| No state progress for `config.stall_rounds` rounds | Broker emits `stall` and prompts mediator input. |
| Snapshot exceeds byte ceiling | Broker emits truncation event and marks snapshot incomplete. |
| `spec` before closure | `spec` exits nonzero with unresolved question IDs. |

## Testing strategy

The eval suite must discriminate. Each test includes a seeded defect that the
gate catches:

1. Replay eval: delete Tier 3 views, rebuild, and require byte-identical output.
2. Payload eval: corrupt `prompt.md` or `final.md`; `rebuild` fails.
3. Snapshot eval: delete scratch worktree; reconstruct captured changes.
4. Truncation eval: exceed byte ceiling; truncation event appears.
5. Protocol eval: seed a contradiction; the next state requires mediator action
   and does not silently treat the contradiction as settled.
6. Spec eval: unsupported decisions, unresolved blocking questions, and missing
   tasks make `spec` fail.
7. Stall eval: seed no-op rounds; broker emits `stall`.
8. Live smoke: one bounded Codex + Claude Code round records `prompt.md`,
   `final.md`, and `participant_final` events for both participants.
9. Availability eval: fake harness adapters cover missing command,
   unauthenticated, subscription-unavailable, usage-limited, rate-limited, and
   unknown-failure results without mutating the manifest.

## Exclusions

Context compression is deferred. The v1 context strategy is deterministic
compact state plus peer `final.md` files. Future compression may create Tier 3
views or compress peer-bound context, but Tier 1 events and Tier 2 payloads stay
original and hashed over originals.

Patch application, promotion, shared worktrees, arbitrary participant counts, and
the web UI are also deferred.

Running `spec-review` inside each participant turn is excluded. The broker
injects repo-contract guidance into prompts; downstream `spec-review` reviews the
generated spec.
