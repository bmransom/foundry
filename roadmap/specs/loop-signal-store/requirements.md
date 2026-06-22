> **Status:** Ready (2026-06-21) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — loop signal store (S1)

The self-improving loop's first buildable piece is its memory: a per-repo store that
records when a Foundry conversation hits a generic capability problem, folds recurrences
of the same cause into a durable candidate, and exposes a reviewable ledger the proposer
(S2) reads later. The store earns its keep by answering three questions and no more:
(a) **surface** a problem that recurs across conversations, (b) **stop surfacing** it once
addressed, and (c) **notice** when an addressed problem comes back.

Two design rules, settled across five mediated deliberations (broker sessions
`reg-determinism`, `learning-bar`, `version-fragility`, `simplicity-audit`,
`local-multirepo`), keep S1 small and verifiable:

- **State admission is deterministic.** A CLI owns every transition that changes consent,
  identity, counters, attribution, committed state, or off-host emission. Agents draft;
  the script admits. This must hold across both harnesses (Claude Code and Codex), so the
  store is a plain portable CLI any harness, git hook, human, or CI can run.
- **The committed record is a closed schema.** Off-host-bound and committed records carry
  only enums, hashes, counters, and bounded fields — never unbounded free text. Closing
  the channel is the privacy lever; the redaction gate guards what a closed field cannot.

Liveness and regression are **computed from the append-only log**, not from version
comparison: the log is already a total order. A build identity is stored as an **opaque
label, never compared** in v1 — the seam that lets a later multi-version phase add ordering
without a migration.

This spec covers the **single-repo, local** S1 store. Cross-repo aggregation on one
machine is the sibling spec `local-multirepo-aggregate` (it reads this store, unchanged).
The proposer (S2), consult/selection (S3), and build pipeline (S4) are separate specs that
read this store; this spec names the seams and stops there. External telemetry and all
version/registry/k-anonymity machinery are out of scope and Backlog (see Out of scope).

## User stories

### US-1: Split the store by signal sensitivity

As a Foundry maintainer, I want raw signals quarantined in a gitignored zone and only
generic summaries committed, so a fresh clone carries the loop's memory without ever
carrying user-specific raw text.

Acceptance criteria:

- AC-1.1 WHEN the store writes a raw signal payload, THE SYSTEM SHALL write it under
  `.foundry/tmp/self-improvement/` (already gitignored) and SHALL NOT write raw signal
  text under `.foundry/state/`.
- AC-1.2 WHEN the store writes a candidate ledger record, THE SYSTEM SHALL write it under
  `.foundry/state/self-improvement/` (tracked, not gitignored).
- AC-1.3 WHEN the committed ledger references a raw signal, THE SYSTEM SHALL reference it
  by SHA-256 hash and generic summary only, and SHALL NOT copy the raw payload's bytes
  into the committed zone.
- AC-1.4 WHEN the store starts, THE SYSTEM SHALL record the repo root and the store schema
  version in a `store_started` event.

### US-2: Append-only ledger, immutable payloads, rebuildable views, closed v1 event set

As a Foundry maintainer, I want the store built on the broker's storage discipline —
append-only event ledger, immutable hashed payloads, rebuildable views — and a small
closed event set, so corruption is detectable, history is never rewritten, and the v1
model stays legible.

Acceptance criteria:

- AC-2.1 WHEN the store records an event, THE SYSTEM SHALL append it to a JSONL ledger with
  a monotonic event id, a creation timestamp, and the store id, and SHALL NOT mutate an
  existing event.
- AC-2.2 WHEN the store writes a payload that already exists with different bytes, THE
  SYSTEM SHALL refuse the write as an immutable-payload violation.
- AC-2.3 WHEN the store records a payload reference, THE SYSTEM SHALL store the payload's
  relative path and SHA-256 hash, and the path SHALL stay within the store directory (no
  absolute path, no `..`).
- AC-2.4 WHEN the store rebuilds its views, THE SYSTEM SHALL re-validate every payload
  reference's hash and SHALL refuse the rebuild if a committed view differs from the
  recomputed view.
- AC-2.5 WHEN the store appends an event, THE SYSTEM SHALL accept only the closed v1 event
  set — `store_started`, `candidate_observed`, `candidate_decision`, `signal_rejected` —
  and SHALL reject an unknown event type.

### US-2b: Serialize concurrent writers under an advisory lock

As a Foundry maintainer, I want the store safe under many concurrent writers — S1 is one
shared per-repo store every source (eval, code-review, dogfood, issue-triage) may write to
at once — so concurrent admits never tear the ledger, never duplicate a candidate, and
never race the write-if-absent payload check. Reads stay lock-free, and a crashed writer
never leaves the store half-applied.

Acceptance criteria:

- AC-2b.1 WHEN the store enters its write critical section — read the current view, decide
  the candidate fold, write-if-absent the payload, append the event(s) — THE SYSTEM SHALL
  hold the store write lock (an advisory `flock` on a lockfile under
  `.foundry/state/self-improvement/`) for the whole section and release it on exit.
- AC-2b.2 WHILE two writers admit concurrently, including a record that exceeds the OS
  atomic-append size, THE SYSTEM SHALL serialize their appends so the JSONL ledger contains
  every event as a whole line and SHALL NOT produce a torn line.
- AC-2b.3 WHEN two concurrent observations carry the same NEW candidate fingerprint, THE
  SYSTEM SHALL record both as `candidate_observed` events folding into one candidate and
  SHALL NOT create two distinct candidates for that fingerprint.
- AC-2b.4 WHEN two concurrent writers write the same payload path, THE SYSTEM SHALL
  serialize the write-if-absent check so identical bytes write once and differing bytes are
  refused as an immutable-payload violation (AC-2.2), with no torn payload.
- AC-2b.5 WHEN the store reads — the proposer (S2) reading a snapshot, or a rebuild
  re-validating hashes — THE SYSTEM SHALL read the append-only ledger without acquiring the
  write lock.
- AC-2b.6 WHEN a writer dies mid-section, THE SYSTEM SHALL release the lock on process death
  (`flock` semantics) and SHALL leave a recoverable store: a rebuild detects a partial
  trailing append by hash/JSON validation and ignores it, never half-applying it.
- AC-2b.7 WHEN the store rebuilds a committed view, THE SYSTEM SHALL write it atomically
  (temp file then rename) so a crash never leaves a partially written view.

### US-3: Ingest from multiple sources behind one gate, with deterministic attribution

As a Foundry maintainer, I want every signal to enter through one admission path that
records its source kind and producing harness deterministically, so the store treats all
sources uniformly, a later source plugs in without a schema change, and attribution cannot
be forged by an agent.

Acceptance criteria:

- AC-3.1 WHEN the store admits an observation, THE SYSTEM SHALL record it as a
  `candidate_observed` event carrying `source_kind`, `source_harness`, a hash-reference to
  the raw payload, and a generic summary.
- AC-3.2 WHEN the store admits an observation, THE SYSTEM SHALL accept `source_kind` from
  the closed set `eval`, `code-review`, `spec-review`, `dogfood`, `issue-triage`,
  `telemetry`, and SHALL reject an unrecognized `source_kind`.
- AC-3.3 WHEN the store records `source_harness`, THE SYSTEM SHALL stamp it adapter-side
  (CLI flag or invoking adapter) verified against the manifest's `harnesses`, and SHALL
  reject an agent-supplied `source_harness`. For a non-harness source (git hook/cron) THE
  SYSTEM SHALL record `source_kind` accordingly and leave `source_harness` null/`system`,
  never a faked harness name.
- AC-3.4 WHEN a new source is added later (e.g. `telemetry`), THE SYSTEM SHALL admit it as
  one more `source_kind` value with no change to the `candidate_observed` event schema.
- AC-3.5 WHEN `source_kind=telemetry` and the `telemetry.enabled` flag
  (`.foundry/self-improvement-config.json`) is OFF, THE SYSTEM SHALL refuse the admission
  and record a `signal_rejected` event with reason `telemetry-disabled`, writing nothing
  else to `.foundry/state/`.
- AC-3.6 WHEN the `telemetry.enabled` flag is unset, THE SYSTEM SHALL treat telemetry as
  OFF (default-off), so AC-3.5 applies.
- AC-3.7 WHEN `source_kind` is an internal source (`eval`, `code-review`, `spec-review`,
  `dogfood`, `issue-triage`), THE SYSTEM SHALL admit it regardless of the
  `telemetry.enabled` flag.

### US-4: Closed-schema committed record behind a fail-closed redaction gate

As a Foundry maintainer, I want every committed record to be a closed schema — bounded
fields, no free text — and a fail-closed redaction gate over the zone crossing, so
raw-signal leakage is structurally impossible, not a matter of remembering.

Acceptance criteria:

- AC-4.1 WHEN a committed-bound record carries an unbounded free-text field, THE SYSTEM
  SHALL reject it; the committed schema admits only enums, hashes, counters, and bounded
  fields.
- AC-4.2 WHEN a committed-bound record contains an absolute filesystem path, a recognized
  secret token, or a PII pattern (e.g. email), THE SYSTEM SHALL reject it (fail-closed).
- AC-4.3 WHEN the redaction gate rejects a record, THE SYSTEM SHALL record a
  `signal_rejected` event naming the marker class only, and the event SHALL NOT carry the
  matched raw text.
- AC-4.4 WHEN the redaction gate rejects a record, THE SYSTEM SHALL NOT write any rejected
  content to `.foundry/state/`.
- AC-4.5 WHEN the redaction gate runs against its seeded fixture, THE SYSTEM SHALL fail if a
  planted raw-leak (a path, secret, PII string, or free-text field in a committed record)
  passes the gate, and SHALL fail if a clean decoy is wrongly rejected.
- AC-4.6 WHEN the store admits a `candidate_observed`, THE SYSTEM SHALL stamp, in bounded
  closed-schema fields: `build_kind` and an opaque `build_label` (NEVER compared in v1),
  `convention_version` (stamped, never gated in v1), `fingerprint_version`, and
  `origin`/`origin_chain` (carrying the `loop_generated` flag).

### US-5: Surface a candidate by conversation-recurrence within a recency window

As a Foundry maintainer, I want a candidate to surface when its cause recurs across enough
distinct conversations recently, so a real repeating problem is surfaced while a single
conversation's noise is not, and an old occurrence ages out on its own.

Acceptance criteria:

- AC-5.1 WHEN the store admits a `candidate_observed`, THE SYSTEM SHALL stamp a
  deterministic `conversation_id` and `root_conversation_id`; for a consumer's own session
  the `conversation_id` SHALL be a hash of the harness-native session id stamped
  adapter-side, and an agent-supplied id SHALL be rejected.
- AC-5.2 WHEN the store counts recurrence for the surfacing bar, THE SYSTEM SHALL count
  **distinct `root_conversation_id`**, so retries, resumed turns, and spawned child sessions
  (which share a root) raise only the within-conversation occurrence count, never the
  bar-bearing count.
- AC-5.3 WHEN the store evaluates whether a candidate is live, THE SYSTEM SHALL apply a
  **recency window** (a maintainer-configurable count of distinct roots or number of days,
  with a stated default) and SHALL count only observations inside the window; a candidate is
  live WHEN its in-window distinct-root count is at least the threshold N and no later
  `candidate_decision` applies.
- AC-5.4 WHEN the store excludes observations from the surfacing bar by the recency window,
  THE SYSTEM SHALL record what the window excluded (no silent truncation).
- AC-5.5 WHILE a candidate's supporting evidence descends from the loop's own DESIGN OUTPUT
  (a prior proposal re-entering as a signal — `origin_chain` carries `loop_generated`), THE
  SYSTEM SHALL quarantine it: such a candidate alone SHALL NOT reach the proposer regardless
  of its distinct-root count.
- AC-5.6 WHEN an observation is a foundry-skill OPERATIONAL failure experienced during loop
  execution (e.g. a deliberation turn that hit a broker bug), THE SYSTEM SHALL capture it as
  a normal capability-gap candidate and SHALL NOT quarantine it as `loop_generated` — the
  quarantine targets loop design output re-entering as evidence, not operational failures of
  the skills the loop runs.

### US-6: Aggregate observations into a candidate by normalized cause

As a Foundry maintainer, I want recurring observations folded into a durable candidate that
fingerprints the **normalized cause, not the conversation**, so the ledger names a generic
problem the proposer can rank — and so the same cause fingerprints identically across repos
(the join key the sibling cross-repo spec relies on).

Acceptance criteria:

- AC-6.1 WHEN the store fingerprints a candidate, THE SYSTEM SHALL derive it from the
  normalized cause (a closed-enum tuple of category, affected surface, failure mode,
  evidence kind) and SHALL exclude raw text, paths, repo names, timestamps, and local
  identifiers — so the fingerprint is repo-independent by construction.
- AC-6.2 WHEN a new observation matches an existing candidate's fingerprint, THE SYSTEM SHALL
  fold it in as another `candidate_observed` and SHALL NOT create a second candidate for
  that fingerprint.
- AC-6.3 WHEN the store records the fingerprint, THE SYSTEM SHALL stamp `fingerprint_version`
  so the normalization algorithm can evolve without orphaning prior events.
- AC-6.4 WHEN the store renders its committed views, THE SYSTEM SHALL produce a
  human-readable candidate ledger digest from the events alone, rebuildable from the ledger.
- AC-6.5 WHEN the store maps a cause to its `failure_mode`, THE SYSTEM SHALL use a closed
  per-`affected_surface` `failure_mode` enum, so the fingerprint is script-canonicalized from
  the closed `(affected_surface, failure_mode)` tuple, not from agent free-form text — the
  cross-repo join key. (The spike proved agents produce divergent free-form slugs for one
  cause while the closed `affected_surface` enum aligns.)

### US-7: Record one candidate decision; compute liveness and regression

As a Foundry maintainer, I want resolution to be one explicit event with regression computed
from the log, so a fixed problem stops surfacing, a human can dismiss a non-problem without
opening a COE, and a recurrence after a decision is flagged for review — all without version
comparison.

Acceptance criteria:

- AC-7.1 WHEN a candidate is decided, THE SYSTEM SHALL record exactly one
  `candidate_decision` event with a `disposition` from the closed set
  `resolved | dismissed | duplicate | wontfix`, a `decision_source` (`human | coe | board`),
  and bounded `provenance_refs[]` (e.g. `coe_id`, `board_card`, `release_tag`, `spec_slug`,
  `eval_id`) — never a raw path.
- AC-7.2 WHEN a candidate has an effective `candidate_decision` and no later qualifying
  observation in the recency window, THE SYSTEM SHALL treat it as quiet and SHALL NOT surface
  it.
- AC-7.3 WHEN a `candidate_observed` postdates a candidate's last `candidate_decision` within
  the recency window, THE SYSTEM SHALL compute the candidate as `regression-suspected` and
  route it to review — never auto-act, never auto-resolve, never auto-suppress.
- AC-7.4 WHEN the store computes liveness, regression, suppression, or any per-candidate
  status, THE SYSTEM SHALL derive it from the append-only event stream and SHALL NOT store a
  `reopened`, `suppressed`, or `regressed` event.
- AC-7.5 WHEN any consumer requests an automatic suppression or action on the resolution
  signal, THE SYSTEM SHALL refuse it in v1; automatic action requires version comparison,
  which is deferred (see Out of scope). The opaque `build_label` is the seam that makes that
  later addition migration-free.

### US-8: Expose a read contract and non-foreclosing seams

As a downstream author (S2 proposer, the local-multirepo aggregator, later external
telemetry), I want a documented read contract and named extension seams, so I read the store
without reaching into its internals and the deferred phases plug in without reopening this
spec.

Acceptance criteria:

- AC-8.1 WHEN the proposer (S2) reads the store, THE SYSTEM SHALL expose live candidates and
  their evidence through the rebuildable committed view, and SHALL NOT require the reader to
  parse raw payloads.
- AC-8.2 WHEN the store is read on a fresh clone with no `.foundry/tmp/` zone, THE SYSTEM
  SHALL still expose the committed candidate ledger from `.foundry/state/`.
- AC-8.3 WHEN the local-multirepo aggregator reads this store, THE SYSTEM SHALL expose the
  committed ledger as a pure read with the per-repo schema unchanged; `source_repo` is the
  reader's read-time annotation and SHALL NOT be a field this store emits.
- AC-8.4 WHEN a deferred phase is added later (external telemetry, version ordering,
  cross-repo counts), THE SYSTEM SHALL require no S1 schema change beyond a new `source_kind`
  value or a new materialized view over the existing fields.
- AC-8.5 WHEN a reader requests candidate evidence, THE SYSTEM SHALL expose the per-
  `source_harness` breakdown (claude-code vs codex), so a gap concentrated on one harness's
  adapter is distinguishable from one seen across both harnesses (stronger generic evidence).

### US-9: Capture observations from tiered sources

As a Foundry maintainer, I want observations captured from the highest-fidelity source
available — a foundry skill's own structured failure events first, ambient transcript
friction second — so the loop learns from operational signal it already emits and from
friction it doesn't, with the deterministic/judgment split explicit.

Acceptance criteria:

- AC-9.1 WHEN a foundry skill emits a structured operational failure (e.g. the
  harness-deliberation broker's `participant_failed`), THE SYSTEM SHALL admit it as a
  `candidate_observed` directly (Tier 1: deterministic, no transcript scan, no agent
  scope-filter), carrying `source_kind`, `source_harness`, and the failure detail mapped to
  the closed `failure_mode` enum.
- AC-9.2 WHEN capturing ambient friction from a conversation transcript (Tier 2), THE SYSTEM
  SHALL first narrow deterministically (a foundry-mechanism marker within a proximity window
  of a failure marker), then an agent SHALL apply the capture SCOPE-FILTER before a
  `candidate_observed` is admitted.
- AC-9.3 WHEN the capture scope-filter runs, THE SYSTEM SHALL treat it as distinct from the
  genericity gate: the scope-filter decides in/out of the foundry-mechanism domain (a
  foundry gap vs a repo-domain bug); the genericity judgment (overfit) is deferred to S2.
- AC-9.4 WHEN a Tier-2 capture pass scores transcripts, THE SYSTEM SHALL surface top-N
  candidate spans relative to the transcript (no absolute threshold) and SHALL attribute each
  to its `root_conversation_id` so subagent/child sessions fold into their root.

## Out of scope

Deferred to a clearly later phase, each with its buyer named:

- **Version comparison and ordering** (release registry, registry-index gate key, SemVer
  comparator, git-ancestry dev ordering, `fixed_in_release_index`, two-axis plugin/convention
  gating, `counts_by_version` as a gate input). Buyer: the multi-version external aggregate.
  v1 stores an opaque `build_label`, never compared (US-7). The full hardened design is
  recorded (broker session `version-fragility`) for that phase.
- **Cross-repo aggregation** (`distinct_repo`, the user-level registry, the pull aggregator,
  `source_repo`). Buyer: one developer's many repos on one machine — the sibling spec
  `local-multirepo-aggregate`, which reads this store unchanged.
- **The genericity gate** (rejecting too-specific/overfit candidates). On a repo's own data
  the privacy rationale is moot and overfit is a judgment — it belongs to S2/human selection,
  not S1 admission. v1 keeps only fingerprint normalization, not a separate genericity gate.
- **External telemetry** ingestion and anonymization (k-anonymity, pseudonymous install ids,
  `distinct_install`, cross-tenant aggregation, the off-host export, the re-identification
  eval). Backlog; S1 only names the `source_kind=telemetry` seam and its default-off gate.
- **Fields cut from v1**: `parent_conversation_id`, `attempt_id`,
  `occurrence_count_in_conversation` as a committed field, `repo_commit`, `manifest_sha256`.
  `root_conversation_id` defaults to `conversation_id` when the harness reports no parent.
- The shared `AppendOnlyStore` base-class extraction from the broker — a separate refactor
  this build may depend on (see design Dependencies). S1 may start on copied mechanics
  guarded by its own discrimination tests.
- The proposer (S2), consult/selection (S3), and build pipeline (S4).
- The bootstrap/update prompt that sets `telemetry.enabled` (default off) — owned by the
  external-telemetry epic. S1 only *reads* the flag.

## Dependencies

- Foundry's two-zone convention: `.foundry/tmp/` is gitignored (raw zone); `.foundry/state/`
  is committed (generic ledger).
- `.foundry/manifest.json` provides `harnesses` (for the `source_harness` check),
  `pluginVersion`, and `conventionVersion`.
- The redaction gate carries its own discriminating eval (US-4); the determinism partition
  and closed-schema rule (broker session `reg-determinism`) govern admission.
- Optional: the `AppendOnlyStore` extraction (Out of scope) — if unavailable, S1 starts on
  storage mechanics copied from the broker's `SessionStore`.
