> **Status:** In progress (2026-06-19) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — harness deliberation

## User stories

### US-1: Start a mediated two-harness design session

As a Foundry user, I want to start a Codex + Claude Code design session from a
consumer repo so both harnesses challenge assumptions and produce an
implementation-ready spec with recorded evidence.

Acceptance criteria:

- AC-1.1 WHEN the user starts a harness deliberation with a prompt or prompt
  file, THE SYSTEM SHALL create a session directory under
  `.foundry/tmp/harness-deliberation/<session-id>/`.
- AC-1.2 WHEN the session starts, THE SYSTEM SHALL record `session_started` and
  `mediator_prompt` events in an append-only `events.jsonl` ledger.
- AC-1.3 WHEN `.foundry/manifest.json` does not include both `claude-code` and
  `codex`, THE SYSTEM SHALL refuse to start and report the missing harness set.
- AC-1.4 WHEN `tmux`, `claude`, `codex`, `git worktree`, or
  `harness-status.py` fails, THE SYSTEM SHALL fail preflight with the failed
  command and harness availability result.
- AC-1.5 WHEN preflight passes, THE SYSTEM SHALL open a tmux view with the
  Codex pane, Claude Code pane, transcript, current state, and mediator command
  pane.
- AC-1.6 WHEN `start --attach` runs from an interactive terminal, THE SYSTEM
  SHALL attach the user to the tmux session; otherwise it SHALL print the exact
  `tmux attach -t <session>` command.

### US-2: Exchange peer-readable turns without raw-log leakage

As a mediator, I want each harness to read compact state and the peer's final
message, not raw terminal streams, so each turn stays focused and auditable.

Acceptance criteria:

- AC-2.1 WHEN the broker runs a participant turn, THE SYSTEM SHALL write the
  exact prompt to `turns/<turn-id>-<actor>/prompt.md`.
- AC-2.2 WHEN the participant finishes, THE SYSTEM SHALL write the peer-readable
  response to `turns/<turn-id>-<actor>/final.md`.
- AC-2.3 WHEN the participant produces raw CLI output, THE SYSTEM SHALL store it
  as debug-only evidence under the turn directory and SHALL NOT require peers,
  `rebuild`, or `spec` to read it.
- AC-2.4 WHEN the broker records a turn, THE SYSTEM SHALL append an event naming
  `prompt.md`, `final.md`, and their SHA-256 hashes.
- AC-2.5 WHEN a payload hash does not match the ledger, THE SYSTEM SHALL fail
  `rebuild` and name the corrupted path.
- AC-2.6 WHEN the broker renders a participant prompt, THE SYSTEM SHALL include
  required repo guidance paths for standing rules, glossary, spec format, and
  board state, plus optional paths for feature conventions, gate inventory,
  active spec files, and discovered architecture concept paths when those files
  exist.
- AC-2.7 WHEN repo guidance is included in a prompt, THE SYSTEM SHALL record a
  `repo_guidance` event with each guidance path, role, required flag, and content
  hash when the file exists.
- AC-2.8 WHEN a required repo guidance source is missing, THE SYSTEM SHALL fail
  preflight and report the missing path.
- AC-2.9 WHEN the mediator runs `round`, THE SYSTEM SHALL run one Codex turn and
  one Claude Code turn, assign both turns the same round ID, and alternate the
  participant that runs first each round.

### US-3: Preserve an auditable session record

As a maintainer, I want the session record to be replayable and tamper-evident
so generated specs can cite evidence rather than trust the broker.

Acceptance criteria:

- AC-3.1 WHEN the broker writes `events.jsonl`, THE SYSTEM SHALL append events
  only; revisions SHALL be new events that supersede earlier ones.
- AC-3.2 WHEN `rebuild` runs, THE SYSTEM SHALL regenerate `state.json`,
  `state.md`, and `transcript.md` from `events.jsonl` and immutable payloads.
- AC-3.3 WHEN rebuilt Tier 3 views differ from the existing Tier 3 views in the
  session directory, THE SYSTEM SHALL report the differing view and exit nonzero.
- AC-3.4 WHEN `events.jsonl` references a missing payload, THE SYSTEM SHALL fail
  `rebuild` and report the missing relative path.
- AC-3.5 WHEN a decision is revised, THE SYSTEM SHALL retain the old and new
  events and expose only the latest effective disposition in `state.json`.

### US-4: Let the mediator steer without hiding dissent

As a mediator, I want to decide which conclusions are settled, rejected, or
deferred dissent so the final spec converges without pretending all objections
were resolved.

Acceptance criteria:

- AC-4.1 WHEN the mediator records a decision, THE SYSTEM SHALL require one
  disposition: `settled`, `rejected`, or `deferred-dissent`.
- AC-4.2 WHEN a decision is `settled`, THE SYSTEM SHALL make it eligible for
  requirements, design, or tasks output with traceability.
- AC-4.3 WHEN a decision is `rejected`, THE SYSTEM SHALL keep it in the event
  log and omit it from generated spec content.
- AC-4.4 WHEN a decision is `deferred-dissent`, THE SYSTEM SHALL carry it into
  `design.md` as a named tradeoff with event references.
- AC-4.5 WHEN `config.stall_rounds` consecutive rounds leave
  `last_progress_hash` unchanged, THE SYSTEM SHALL emit a `stall` event and wait
  for mediator input.

### US-5: Capture scratch implementation evidence without integrating patches

As a participant, I want to use scratch worktrees as evidence while keeping the
consumer repo untouched until the mediator chooses implementation work.

Acceptance criteria:

- AC-5.1 WHEN the broker creates participant worktrees, THE SYSTEM SHALL create
  separate Codex and Claude Code worktrees on separate branches.
- AC-5.2 WHEN the mediator requests a snapshot, THE SYSTEM SHALL capture the base
  commit, `git diff --binary` tracked diff, untracked byte payloads, untracked
  file index, byte counts, and hashes as portable Tier 2 payloads.
- AC-5.3 WHEN a snapshot exceeds the byte ceiling, THE SYSTEM SHALL emit a
  truncation event and mark the snapshot incomplete.
- AC-5.4 WHEN the original scratch worktree is deleted and the snapshot is not
  marked incomplete, THE SYSTEM SHALL still be able to reconstruct the captured
  snapshot from recorded payloads.
- AC-5.5 WHEN a participant proposes applying or promoting work, THE SYSTEM
  SHALL record the proposal as a design decision request and SHALL NOT mutate the
  consumer repo worktree.

### US-6: Generate a Foundry spec only after closure

As a maintainer, I want `spec` to require a passing `rebuild` and closed
questions so the output cites verified events and dispositions.

Acceptance criteria:

- AC-6.1 WHEN `spec` runs before `rebuild` passes, THE SYSTEM SHALL refuse and
  report that `rebuild` has not passed for the current session record.
- AC-6.2 WHEN any question lacks `settled`, `rejected`, or
  `deferred-dissent`, THE SYSTEM SHALL refuse `spec` and report the question ID.
- AC-6.3 WHEN `spec` succeeds, THE SYSTEM SHALL write
  `roadmap/specs/<feature>/{requirements,design,tasks}.md`.
- AC-6.4 WHEN `spec` writes a requirement or major design choice, THE SYSTEM
  SHALL include traceability to the governing decision event ID and supporting
  payload hash.
- AC-6.5 WHEN the session contains `deferred-dissent`, THE SYSTEM SHALL include a
  tradeoff section in `design.md`.
- AC-6.6 WHEN `spec` succeeds, THE SYSTEM SHALL report that per-turn repo
  guidance does not replace downstream `spec-review` before approval.

### US-7: Keep the first release intentionally narrow

As a Foundry maintainer, I want v1 to prove the protocol before adding a web UI,
compression, or patch integration.

Acceptance criteria:

- AC-7.1 WHEN v1 runs a session, THE SYSTEM SHALL support exactly two
  participants: Codex and Claude Code.
- AC-7.2 WHEN v1 presents the session, THE SYSTEM SHALL expose a tmux/TUI view
  and SHALL NOT require a web UI.
- AC-7.3 WHEN v1 builds participant context, THE SYSTEM SHALL NOT include
  context compression.
- AC-7.4 WHEN v1 captures scratch implementation evidence, THE SYSTEM SHALL NOT
  include `/apply`, `/promote`, or shared-worktree mutation.
- AC-7.5 WHEN v1 documents future work, THE SYSTEM SHALL name web UI,
  compression, more than two participants, and patch promotion as deferred.

### US-8: Detect harness availability drift and usage limits

As a Foundry maintainer, I want Foundry to detect when a manifest-selected
harness is locally unavailable so the repo intent and the user's active
subscriptions do not silently drift apart.

Acceptance criteria:

- AC-8.1 WHEN bootstrap verify, `/foundry:update`, or harness deliberation reads
  `.foundry/manifest.json` `harnesses`, THE SYSTEM SHALL run bounded harness
  availability checks for each selected harness.
- AC-8.2 WHEN a selected harness command, auth check, or bounded live-turn check
  fails, THE SYSTEM SHALL report one harness availability result:
  `missing-command`,
  `not-authenticated`, `subscription-unavailable`, `usage-limited`,
  `rate-limited`, or `unknown-failure`.
- AC-8.3 WHEN a selected harness is unavailable, THE SYSTEM SHALL ask whether
  the repo's intended harness set changed and offer `/foundry:update` to remove
  or add a harness; it SHALL NOT edit `.foundry/manifest.json` automatically.
- AC-8.4 WHEN a participant hits a usage or rate limit during `round`, THE
  SYSTEM SHALL append a `participant_limited` event, preserve the session, pause
  further turns for that participant, and report retry, stop, and
  `/foundry:update` options to the mediator.
- AC-8.5 WHEN `/foundry:update` removes a harness, THE SYSTEM SHALL update only
  `.foundry/manifest.json` `harnesses` and that harness's shim, leave shared
  files such as `AGENTS.md` untouched, and refuse to remove the last harness.
- AC-8.6 WHEN harness deliberation requires a participant that is unavailable or
  no longer selected in the manifest, THE SYSTEM SHALL refuse `start` or `round`
  and point to the auth/subscription fix or `/foundry:update` for changing the
  manifest harness set.

## Out of scope

- A general deliberation product outside Foundry.
- A web dashboard or browser UI.
- Arbitrary participant counts.
- Automatic patch merge, apply, or promote flows.
- Context compression on the critical path.
- Bootstrap forcing users to install `tmux`, `claude`, or `codex`; deliberation
  owns its own preflight.
- Running `spec-review` inside every participant turn.
- Automatically removing a harness from the manifest because one user's local
  account or quota check failed.
