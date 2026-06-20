> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — loop signal store (S1)

The self-improving loop's first buildable piece is its memory: a store that
ingests signals (eval metrics, dogfood findings, GitHub issues), aggregates them
into durable candidate problems, and exposes a reviewable ledger the proposer
cron (S2) ranks later. The store splits by signal sensitivity. Raw signals —
conversation excerpts, issue bodies, eval transcripts — carry user-specific text
and live in a gitignored zone. The candidate ledger is generic-by-construction
and committed, so the loop's memory survives a fresh clone
and ranking stays reviewable in a pull request. A redaction gate is the structural
defense between the two zones: nothing reaches the committed ledger without passing
it, and a seeded raw-leak must make the gate fail.

This spec covers S1 only. The proposer (S2), consult / A-B selection (S3), and
build pipeline (S4) are separate specs that read this store; this spec names the
seams they plug into and stops there.

## User stories

### US-1: Split the store by signal sensitivity

As a Foundry maintainer, I want raw signals quarantined in a gitignored zone and
only generic summaries committed, so a fresh clone carries the loop's memory
without ever carrying user-specific raw text.

Acceptance criteria:

- AC-1.1 WHEN the store writes a raw signal payload, THE SYSTEM SHALL write it
  under `.foundry/tmp/self-improvement/` (already gitignored) and SHALL NOT write
  raw signal text under `.foundry/state/`.
- AC-1.2 WHEN the store writes a candidate ledger record, THE SYSTEM SHALL write
  it under `.foundry/state/self-improvement/` (tracked by default, not gitignored).
- AC-1.2b WHEN the store writes a metric ledger record, THE SYSTEM SHALL write it
  under `.foundry/state/self-improvement/` (tracked by default, not gitignored).
- AC-1.3 WHEN the committed ledger references a raw signal, THE SYSTEM SHALL
  reference it by SHA-256 hash and generic summary only, and SHALL NOT copy the
  raw payload's bytes into the committed zone.
- AC-1.4 WHEN the store starts, THE SYSTEM SHALL record the repo root and the
  store schema version in a `store_started` event.

### US-2: Reuse the append-only / immutable-payload / rebuildable-view pattern

As a Foundry maintainer, I want the store built on the same storage discipline as
the broker — append-only event ledger, immutable hashed payloads, rebuildable
views — so corruption is detectable and history is never rewritten.

Acceptance criteria:

- AC-2.1 WHEN the store records an event, THE SYSTEM SHALL append it to a JSONL
  ledger with a monotonic event id, a creation timestamp, and the store id, and
  SHALL NOT mutate an existing event.
- AC-2.2 WHEN the store writes a payload that already exists with different bytes,
  THE SYSTEM SHALL refuse the write as an immutable-payload violation.
- AC-2.3 WHEN the store records a payload reference, THE SYSTEM SHALL store the
  payload's relative path and SHA-256 hash, and the path SHALL stay within the
  store directory (no absolute path, no `..`).
- AC-2.4 WHEN the store rebuilds its views, THE SYSTEM SHALL re-validate every
  payload reference's hash and SHALL refuse the rebuild if a committed view differs
  from the recomputed view.
- AC-2.5 WHEN the store appends an event, THE SYSTEM SHALL accept only a
  loop-specific closed event-type set and SHALL reject an unknown event type.

### US-2b: Serialize concurrent writers under an advisory lock

As a Foundry maintainer, I want the store safe under many concurrent writers —
unlike the broker's per-session `SessionStore`, S1 is one shared store every
source (eval, code-review, dogfood, issue-triage, telemetry) writes to at once —
so concurrent ingests never tear the ledger, never open a duplicate candidate,
and never race the write-if-absent payload check. Reads stay lock-free, and a
crashed writer never leaves the store half-applied.

Acceptance criteria:

- AC-2b.1 WHEN the store enters its write critical section — read the current
  view, decide open-or-revise candidate and write-if-absent payload, append the
  event(s) — THE SYSTEM SHALL hold the store write lock (an advisory `flock` on a
  lockfile under `.foundry/state/self-improvement/`) for the whole section and
  release it on exit.
- AC-2b.2 WHILE two writers ingest concurrently, including a record that exceeds
  the OS atomic-append size, THE SYSTEM SHALL serialize their appends so the JSONL
  ledger contains every event as a whole line and SHALL NOT produce a torn line.
- AC-2b.3 WHEN two concurrent ingests carry the same NEW fingerprint, THE SYSTEM
  SHALL open at most one candidate and fold the second into it via
  `candidate_revised`, and SHALL NOT emit two `candidate_opened` events for that
  fingerprint.
- AC-2b.4 WHEN two concurrent ingests write the same payload path, THE SYSTEM
  SHALL serialize the write-if-absent check so identical bytes write once and
  differing bytes are refused as an immutable-payload violation (AC-2.2), with no
  torn payload.
- AC-2b.5 WHEN the store reads — the proposer (S2) reading a snapshot, or a
  rebuild re-validating hashes — THE SYSTEM SHALL read the append-only ledger
  without acquiring the write lock.
- AC-2b.6 WHEN a writer dies mid-section, THE SYSTEM SHALL release the lock on
  process death (`flock` semantics) and SHALL leave a recoverable store: a
  rebuild detects a partial trailing append by hash/JSON validation and ignores
  it, never half-applying it.
- AC-2b.7 WHEN the store rebuilds a committed view, THE SYSTEM SHALL write it
  atomically (temp file then rename) so a crash never leaves a partially written
  view.

### US-3: Ingest signals from multiple sources behind one redaction gate

As a Foundry maintainer, I want every signal — eval metric, dogfood finding, or
GitHub issue — to enter through one ingest path that records its source, so the
store treats all sources uniformly and a later source plugs in without a schema
change.

Acceptance criteria:

- AC-3.1 WHEN the store ingests a signal, THE SYSTEM SHALL record a
  `signal_ingested` event carrying a `source_kind` field, a hash-reference to the
  raw payload, and a generic summary.
- AC-3.2 WHEN the store ingests a signal, THE SYSTEM SHALL accept `source_kind` from
  the closed set `eval`, `code-review`, `spec-review`, `dogfood`, `issue-triage`,
  `telemetry`, and SHALL reject an unrecognized `source_kind`.
- AC-3.3 WHEN the store ingests an eval metric sample, THE SYSTEM SHALL record a
  `metric_observed` event derived from the `summary` record `evals/harness/score_review.py`
  emits — `fixture`, `runs`, `mean_recall`, `decoy_hits`, `verdict`.
- AC-3.4 WHEN a new external source is added later (e.g. `telemetry`), THE SYSTEM
  SHALL ingest it as one more `source_kind` value with no change to the
  `signal_ingested` event schema.
- AC-3.5 WHEN `source_kind=telemetry` and the `telemetry.enabled` flag
  (`.foundry/self-improvement-config.json`) is OFF, THE SYSTEM SHALL refuse the
  ingestion and record a `signal_rejected` event with reason `telemetry-disabled`,
  writing nothing else to `.foundry/state/`.
- AC-3.6 WHEN the `telemetry.enabled` flag is unset, THE SYSTEM SHALL treat telemetry
  as OFF (default-off), so AC-3.5 applies.
- AC-3.7 WHEN `source_kind` is an internal source (`eval`, `code-review`,
  `spec-review`, `dogfood`, `issue-triage`), THE SYSTEM SHALL ingest it regardless of
  the `telemetry.enabled` flag.

### US-4: Reject a signal that fails the redaction gate

As a Foundry maintainer, I want a signal whose committed summary carries raw text
— a filesystem path, a secret, or PII — to be rejected before it reaches the
committed ledger, so raw-signal leakage is structurally impossible, not a matter
of remembering.

Acceptance criteria:

- AC-4.1 WHEN a committed-bound record contains an absolute filesystem path, THE
  SYSTEM SHALL reject it.
- AC-4.2 WHEN a committed-bound record contains a recognized secret token, THE
  SYSTEM SHALL reject it.
- AC-4.3 WHEN a committed-bound record contains an email address or other PII
  pattern, THE SYSTEM SHALL reject it.
- AC-4.4 WHEN the redaction gate rejects a record, THE SYSTEM SHALL record a
  `signal_rejected` event naming the marker class, and the event SHALL NOT carry
  the matched raw text.
- AC-4.5 WHEN the redaction gate rejects a record, THE SYSTEM SHALL NOT write any
  rejected content to `.foundry/state/`.
- AC-4.6 WHEN a signal is rejected as duplicate, overfit, private, or out of scope,
  THE SYSTEM SHALL record a `signal_rejected` event naming the reason.
- AC-4.7 WHEN the redaction gate runs against its seeded fixture, THE SYSTEM SHALL
  fail if a planted raw-leak (a path, secret, or PII string in a committed summary)
  passes the gate.

### US-5: Aggregate signals into committed candidate problems

As a Foundry maintainer, I want recurring signals folded into a durable candidate
that fingerprints the normalized cause, not the conversation, so the ledger names
a generic problem the proposer can rank and challenge.

Acceptance criteria:

- AC-5.1 WHEN the store opens a candidate, THE SYSTEM SHALL record a
  `candidate_opened` event whose fingerprint is derived from
  `source_kind + invariant + failing_signature + affected_surface`, not from raw
  signal text.
- AC-5.2 WHEN a new signal matches an existing candidate's fingerprint, THE SYSTEM
  SHALL fold it into that candidate via a `candidate_revised` event and SHALL NOT
  open a duplicate candidate.
- AC-5.3 WHEN the store records a candidate, THE SYSTEM SHALL carry the candidate
  fields listed in design §Candidate identity and fingerprinting, including the
  fingerprint inputs, the evidence event ids, the genericity rationale, and the
  eval hook.
- AC-5.4 WHEN a candidate is resolved — duplicate, fixed, rejected, or shipped —
  THE SYSTEM SHALL record a `candidate_closed` event naming the resolution.
- AC-5.5 WHEN the store renders its committed views, THE SYSTEM SHALL produce a
  human-readable candidate ledger digest from the events, rebuildable from the
  ledger alone.

### US-6: Expose a read contract for the proposer and a source_kind seam for later

As a downstream author (S2 proposer, later external telemetry), I want a documented
read contract and a named `source_kind` extension seam, so I read the store without
reaching into its internals and a new source plugs in without reopening this spec.

Acceptance criteria:

- AC-6.1 WHEN the proposer (S2) reads the store, THE SYSTEM SHALL expose active
  candidates and their metric trends through the rebuildable committed view, and
  SHALL NOT require the reader to parse raw payloads.
- AC-6.2 WHEN the store is read on a fresh clone with no `.foundry/tmp/` zone, THE
  SYSTEM SHALL still expose the committed candidate ledger from `.foundry/state/`.
- AC-6.3 WHEN external telemetry is added later, THE SYSTEM SHALL require no S1
  schema change beyond a new `source_kind` value and the same redaction gate.

## Out of scope

- The shared `AppendOnlyStore` base-class extraction from the broker — a separate
  refactor PR this build depends on (see design Dependencies). S1 starts on copied
  mechanics guarded by its own discrimination tests.
- The proposer cron (S2): ranking, `proposal_drafted`, the brief payload.
- Consult / A-B selection (S3): the rendered digest and append-only selection
  event.
- The build pipeline (S4): deliberation, spec generation, the consent act gate.
- External telemetry ingestion and anonymization — deferred until the internal loop
  is proven; S1 only names the `source_kind` seam.
- The bootstrap/update prompt that sets the telemetry-enabled flag (default off) —
  owned by the external-telemetry epic. S1 only *reads* the flag; it does not
  implement the prompt (see design Dependencies).
- GitHub issue ingestion mechanics — `issue-triage` plugs into the `signal_ingested`
  path as a `source_kind`; its own spec owns the read-only `gh` ingest.
