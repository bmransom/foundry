> **Status:** In progress (2026-06-19) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — harness deliberation

Waves run top to bottom. Tasks within a wave are parallel unless they name a
dependency.

## Wave 1 — Spec and vocabulary

- [ ] T1: Add `harness-deliberation` spec files and board card —
  `roadmap/specs/harness-deliberation/{requirements,design,tasks}.md`,
  `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` PASS after the spec files
  and board card land. Approval: maintainer approval recorded on the board.
  [AC-7.5]
- [x] T2: Add glossary terms for **Harness availability**, **Broker**,
  **Harness deliberation**, **Participant**, **Mediator**, and **Deferred
  dissent** with provenance, then update the knowledge log and index —
  `knowledge/glossary.md`, `knowledge/log.md`, `knowledge/index.md`. Gate:
  `python3 scripts/knowledge.py check`. [AC-4]
- [x] T3: Run a real harness deliberation session over the draft spec and apply
  accepted findings. Gate: the saved session record includes both participant
  `final.md` payloads, and the board records every accepted finding's disposition
  and spec fix. [AC-2, AC-6]
- [x] T4: Run pre-approval `spec-review` on requirements, design, and tasks;
  apply findings before asking for design approval. Gate: review report has no
  findings, or every finding has a recorded disposition and fix. [Spec README]

## Wave 2 — Session store and replay

- [x] T5: Implement the broker's session writer for `session.json`,
  `events.jsonl`, event IDs, immutable payloads, SHA-256 hashes, and turn
  metadata —
  `plugins/foundry/scripts/harness-deliberation-broker.py`. Gate: unit tests
  cover event append, payload hashing, closed event types, and revision events.
  [AC-2, AC-3]
- [x] T6: Implement Tier 3 view rendering for
  `state.json`, `state.md`, and `transcript.md` (dep T5). Gate: replay test
  deletes Tier 3 and rebuilds byte-identical views. [AC-3]
- [x] T7: Implement `rebuild` with hash, missing-payload, invalid-disposition,
  and nondeterminism failures (deps T5, T6). Gate: seeded corruption test fails
  with the corrupted path. [AC-2.5, AC-3]

## Wave 3 — Broker commands and mediator flow

- [x] T8: Implement preflight and `start`: manifest harness check,
  `plugins/foundry/scripts/harness-status.py`, `tmux`, `git worktree`, session
  creation, `start --attach`, and `control`/`state` tmux windows. Gate:
  preflight tests cover missing command, missing harness, unavailable
  subscription/auth, attach-command output, and required pane names. [AC-1, AC-8]
- [x] T9: Implement `round` for one Codex + Claude Code exchange, with
  final-message capture, peer prompts that include compact state, prior
  `final.md`, and guidance paths but exclude raw logs, and repo guidance paths
  for standing rules, glossary, spec format, feature conventions, gate
  inventory, board, active spec files, and `knowledge/**` architecture concept
  paths (deps T5, T8). Gate:
  fake-participant test proves peers read compact state from `state.json` + prior
  `final.md` + `repo_guidance` event, not raw logs, and raw output does not affect
  rebuild; usage-limit fixture records
  `participant_limited` and pauses the participant. [AC-2, AC-8]
- [x] T10: Implement `decide` with explicit questions, dispositions, revision
  events, and current effective state (deps T6). Gate: tests cover open
  questions, `settled`, `rejected`, `deferred-dissent`, and revision
  supersession. [AC-4]
- [x] T11: Implement stall detection using deterministic progress hashes and
  `session.json` default `config.stall_rounds = 2` (deps T9, T10). Gate: seeded
  no-op rounds emit `stall`. [AC-4.5]

## Wave 4 — Snapshot evidence

- [x] T12: Implement scratch worktree creation for Codex and Claude Code
  branches. Gate: worktree setup test creates separate paths and branches
  without touching the consumer repo worktree. [AC-5.1]
- [x] T13: Implement portable snapshot capture: base commit, `git diff --binary`
  tracked diff, untracked byte payloads, untracked-file index, hashes, byte counts,
  and truncation event (dep T12). Gate: snapshot eval reconstructs after
  deleting the scratch worktree. [AC-5]
- [x] T14: Add byte ceiling and explicit incomplete snapshot behavior (dep T13).
  Gate: seeded oversized snapshot emits truncation event and marks incomplete.
  [AC-5.3]

## Wave 5 — Spec generation

- [x] T15: Implement `spec` closure checks: require `rebuild` to pass and
  require dispositions for every question. Gate: unresolved-question fixture
  exits nonzero with the question ID. [AC-6.1, AC-6.2]
- [x] T16: Generate `requirements.md`, `design.md`, and `tasks.md` with
  traceability from decision event IDs and payload hashes (dep T15). Gate: spec
  eval fails on unsupported decisions or missing traceability. [AC-6.3, AC-6.4]
- [x] T17: Render `deferred-dissent` into `design.md` tradeoffs and omit
  `rejected` decisions from spec content (dep T16). Gate: seeded dissent appears
  in design; seeded rejected item does not. [AC-4.3, AC-4.4, AC-6.5]

## Wave 6 — Skill wrapper and eval wiring

- [x] T18: Add the skill wrapper and runner script —
  `plugins/foundry/skills/harness-deliberation/SKILL.md`,
  `plugins/foundry/skills/harness-deliberation/scripts/spawn-deliberation.sh`.
  Gate: static test confirms the skill delegates to the broker and exposes only
  v1 commands. [AC-1, AC-7]
- [x] T19: Add eval fixtures and eval driver for replay, payload,
  snapshot, truncation, protocol, spec, stall, fake-participant smoke, and
  availability-result cases. Gate: fixture suite fails seeded defects and passes
  clean fixtures, including all harness availability results. [AC-1–AC-8]
- [x] T20: Add an opt-in live smoke command that executes one Codex + Claude Code
  round through the participant payload protocol. Gate: the run records
  `prompt.md`, `final.md`, and `participant_final` events for both participants,
  records the command and result in `knowledge/validation.md`, and leaves the
  consumer repo worktree unchanged. [AC-1, AC-2]
- [x] T21: Update Foundry-wide harness management docs and skill references for
  bootstrap verify, `/foundry:update`, `references/add-harness.md`, and
  validation notes so users can check, add, or remove individual harnesses
  without hand-editing the manifest. Gate: fixtures prove bootstrap verify and
  `/foundry:update` invoke `harness-status.py` without mutating the manifest;
  `/foundry:update` removes one Foundry-managed harness shim, leaves shared files
  untouched, reports a custom shim instead of deleting it, and refuses to remove
  the last harness. [AC-8]
- [x] T22: Wire fast deterministic tests into `scripts/check-fast.sh`. Gate:
  `scripts/check-fast.sh` ends with `check-fast: PASS`. [AC-7]

## Wave 7 — Review and finish

- [x] T23: Re-run `spec-review` on requirements, design, and tasks after any
  implementation-driven spec changes; apply findings. Gate: review report has
  no findings, or every finding has a recorded disposition and fix. [Spec README]
- [x] T24: Run `python3 scripts/knowledge.py check` and regenerate
  `knowledge/index.md`. Gate: knowledge check clean and index current. [T2]
- [x] T25: Run the canonical gate. Gate: `scripts/check-fast.sh` prints
  `check-fast: PASS`.

## Wave 8 — Make `round` real and discriminating (F+E)

Found by dogfooding: `round` was advertised but unwired, the mediator prompt never
reached participants, and the `--seed-defect` eval path asserted nothing. This
wave completes `round` end-to-end and replaces the non-discriminating eval
mechanism.

- [x] T26: Wire the `round` CLI over an existing session —
  `round --session-dir <dir>` resolves the session, reads `repo_root` from
  `session.json`, refuses a missing/mismatched session, and calls `run_round`
  with the real participant runner, one round per invocation. Gate: a test
  drives `round` via the CLI over a prepared session and asserts a new
  `participant_final` per participant; a missing session exits nonzero with the
  path. [AC-2.9, AC-2.11]
- [x] T27: Render the mediator prompt and open questions into the turn prompt —
  `_render_participant_prompt` gains a `# Mediator Prompt` section read from the
  immutable `mediator_prompt` payload, keeping compact state and peer finals (dep
  T26). Gate: a `tests/*_test.sh` runs `run_round` with a fake runner on a session
  carrying a mediator prompt and a seeded question, then asserts the persisted
  `turns/0001-codex/prompt.md` contains the mediator prompt body and the question;
  dropping the `# Mediator Prompt` section fails the test. [AC-2.10]
- [x] T28: Split runner policy from execution and unify on stdin — one shared
  adapter runs Codex/Claude read-only (Codex `--sandbox read-only`, Claude
  `--allowedTools "Read,Grep,Glob"`) with the prompt on stdin; `live-smoke` adds
  its confirm-receipt boundary, the real round adds a structured output contract
  (dep T26). Gate: the existing live-smoke test stays green; a test asserts the
  real-round prompt omits the `# Live Smoke Boundary` and that `raw.log` contains
  no prompt text. [AC-2.2, AC-2.15]
- [x] T29: Record `participant_failed` on unclassified nonzero exits via a
  `ParticipantFailed` exception caught in `run_round`, mirroring
  `participant_limited` (dep T28). Gate: a fake nonzero participant appends
  `participant_failed` with the prompt hash and raw path and pauses the session.
  [AC-2.12]
- [x] T30: Make turns resumable — idempotent prompt write on a matching hash, and
  resume the same `round_id` for participants lacking a final after a
  `limited`/`failed` first participant (deps T26, T29). Gate: re-running `round`
  after a half-written turn raises no immutable-payload error; after a
  limited/failed first participant the second participant's same-round turn still
  runs. [AC-2.13, AC-2.14]
- [x] T31: Replace the non-discriminating eval mechanism with real discrimination
  — retire the `--seed-defect` name grep and its meta-test; add the
  command-surface eval (advertised v1 commands from one canonical source equal the
  broker's subcommands and options) and the mediator-prompt-rendering eval from
  T27 as `tests/*_test.sh` (deps T26, T27). Gate: a doc-only command with no parser fails
  the command-surface eval; both evals run inside `scripts/check-fast.sh`. [AC-7]
- [x] T32: Add a `live-smoke` shape check that rejects an empty or boilerplate
  final and document the residual limit that `round` does not self-validate
  answer quality (dep T28). Gate: a no-op final fails the smoke shape check.
  [AC-1, AC-2]
- [x] T33: Re-run the canonical gate and re-cut the paused release. Gate:
  `scripts/check-fast.sh` prints `check-fast: PASS` with Wave 8 landed. [T22]
  Done: shipped in v0.1.2.

## Wave 9 — Gaps from the T3 dogfood

T3 ran a real Codex + Claude deliberation over this spec (session
`t3-spec-dogfood`; both `final.md` recorded; `rebuild: PASS`; dispositions in the
session record: 7 settled, 1 deferred-dissent, 1 rejected). The settled findings
are tracked here; decision IDs trace to the session.

- [x] T34: Carry each peer's latest `final.md` across rounds, not just the
  current round — `_peer_finals_for_round` is round-scoped, so round 2 opens with
  `# Peer Finals - none`. Gate: a two-round render test fails when round 2's first
  prompt has no prior peer final. [d0001]
- [ ] T35: Make the live `start`/tmux path real and testable — long-lived panes
  that tail status/`final.md`, export `FOUNDRY_HD_SESSION` + print command help,
  and call `render_views()` in `start_session` so `state.md`/`transcript.md` exist
  before the `state` window tails them. Gate: a real-tmux test (not
  `run_tmux=False`) fails on placeholder/exiting panes or missing Tier 3 files.
  [d0002, d0003]
- [ ] T36: Re-run preflight/`_check_harness_statuses` at the top of the `round`
  CLI and refuse drift with auth/subscription or `/foundry:update` guidance. Gate:
  a de-selected or unavailable participant makes `round` exit nonzero before
  spending a turn. [AC-8.6, d0004]
- [ ] T37: Honor AC-1.6 in the CLI — detect `sys.stdout.isatty()` for
  `is_interactive` and print the exact `tmux attach -t …` command on the
  non-interactive `--attach` path. Gate: a non-interactive `start --attach` test
  asserts the printed attach command. [AC-1.6, d0005]
- [ ] T38: Align the `decide` contract — implement Markdown + `decision_id`
  supersession, or correct `SKILL.md`/`design.md` to JSON + event-id; the
  command-surface eval asserts the chosen contract. Gate: the documented `decide`
  input parses. [d0006]
- [x] T39: Route the `ParticipantFailed` raw write through `_format_raw_turn` so a
  failed `raw.log` carries the `prompt_sha256`/command envelope. Gate: a
  failed-turn test asserts `prompt_sha256` in `raw.log`. [AC-2.15, d0007]
- [ ] T40: Resolve the snapshot-surface contradiction (deferred dissent) — expose
  `scratch`/`snapshot`/`reconstruct` subcommands, or explicitly defer
  mediator-triggered snapshots from v1 and reconcile US-5/AC-5.2 with the
  command table. Gate: the command-surface eval and US-5 agree. [d0008]

Rejected (no action): the claim that the success-path raw log leaks `stdout` —
AC-2.15 forbids embedding the prompt, not model output; the success path already
omits the prompt and records `prompt_sha256` (prompt rides stdin). [d0009]
