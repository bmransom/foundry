> **Status:** Ready (2026-06-21) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — local multi-repo aggregate

One developer runs Foundry across many repos on one machine. A generic capability gap that
recurs in several of those repos is stronger evidence of a real Foundry problem than one
that shows up in a single repo. This spec adds a **machine-local, read-only aggregate** that
groups each repo's S1 candidates by their (repo-independent) fingerprint, so the developer —
when improving Foundry — sees "this cause recurred across N of my repos."

It is the **first concrete input to S2's overfit judgment**, and unlike the deferred external
aggregate it has a buyer that exists today (on this machine: `foundry` and `research-rig` are
registered; `octant` enrolls via `/foundry:update`). It deliberately stays small (broker
session `local-multirepo`):

- **Everything is local.** Same developer, same machine, no network. No k-anonymity, no
  pseudonymous install ids, no off-host export — those remain the external-telemetry Backlog.
- **`distinct_repo` is evidence, never a gate.** Cross-repo recurrence is correlated, not
  independent, evidence (clones, forks, shared domain, shared harness). It raises S2 priority;
  it never auto-admits, auto-resolves genericity, or bypasses S2 judgment. The count always
  ships with its **source list** so a human can discount a fork or a domain cluster.
- **The aggregate is a rebuildable view.** It is a pure function of `{registry, each repo's
  ledger-at-read-time}` and is deletable without loss. Per-repo S1 ledgers stay the single
  source of truth; this spec reads them and changes no S1 schema.

This spec depends on `loop-signal-store` (S1) and feeds S2.

## User stories

### US-1: Enroll repos in a machine-local registry

As a developer, I want each Foundry repo enrolled in one machine-local registry, so the
aggregator knows which repos to read without scanning my whole filesystem.

Acceptance criteria:

- AC-1.1 WHEN a repo is bootstrapped or updated, THE SYSTEM SHALL record it in a user-level
  registry `~/.foundry/repos.json` (XDG-respecting if `XDG_DATA_HOME` is set) carrying, per
  repo, a minted stable local `repo_id`, the `path`, the observed `remotes[]`, and an
  `enrolled` flag.
- AC-1.2 WHEN the registry is read, THE SYSTEM SHALL treat enrollment as default-on for a
  bootstrapped/updated repo (the local trust boundary), subject to the opt-out in US-4.
- AC-1.3 WHEN no registry exists, THE SYSTEM SHALL treat the aggregate as empty and SHALL NOT
  scan the filesystem for Foundry repos (no ambient discovery).

### US-2: Aggregate by pull into a deletable view

As a developer, I want the aggregate built by reading each enrolled repo's committed ledger
on demand, so per-repo ledgers stay the single source of truth and the aggregate can be
deleted and rebuilt with no loss.

Acceptance criteria:

- AC-2.1 WHEN the aggregator runs, THE SYSTEM SHALL read each enrolled repo's committed S1
  ledger (`.foundry/state/self-improvement/`) read-only and SHALL NOT write to any per-repo
  ledger.
- AC-2.2 WHEN the aggregator writes its output, THE SYSTEM SHALL write only under a
  machine-local, not-committed aggregate dir (`~/.foundry/aggregate/`), and the aggregate
  SHALL be a pure function of `{registry snapshot, each ledger-at-read-time}`.
- AC-2.3 WHEN the aggregate is deleted and rebuilt from the same inputs, THE SYSTEM SHALL
  produce byte-identical output (deletable without loss; the broker `rebuild` determinism
  check).
- AC-2.4 WHEN the aggregator reads a repo, THE SYSTEM SHALL stamp scan metadata for that repo
  — `HEAD`, dirty flag, and the ledger hash it read — so the view says what it read.
- AC-2.5 WHEN an enrolled repo is missing, moved, not checked out, or carries an invalid
  ledger, THE SYSTEM SHALL skip it and record the reason, and SHALL NOT crash or silently
  drop it.
- AC-2.6 WHEN the aggregator reads ledgers, THE SYSTEM SHALL require no write lock (reads are
  lock-free; a torn trailing JSONL line is detected and skipped), and only the aggregate's
  own single writer SHALL lock.
- AC-2.7 WHEN the aggregator annotates an observation with its `source_repo`, THE SYSTEM SHALL
  add it at read time and SHALL NOT require the per-repo S1 ledger to emit a `source_repo`
  field (S1 schema unchanged).

### US-3: Count distinct repos as evidence, with the source list

As a developer, I want cross-repo recurrence surfaced as evidence with its source list, so I
(or S2) can judge whether it is genuinely generic rather than trusting a bare count.

Acceptance criteria:

- AC-3.1 WHEN the aggregator groups observations, THE SYSTEM SHALL group by the
  repo-independent `candidate_fingerprint` (the S1 join key) and SHALL compute `distinct_repo`
  as the number of distinct repo identity keys (US-4) contributing that fingerprint.
- AC-3.2 WHEN the aggregator reports a fingerprint, THE SYSTEM SHALL surface the **source
  list** — the distinct identity keys with their display paths/remotes — and SHALL NOT report
  `distinct_repo` as a bare count without it.
- AC-3.3 WHEN `distinct_repo >= 2`, THE SYSTEM SHALL treat it as evidence feeding S2 only, and
  SHALL NOT auto-admit a candidate, auto-resolve genericity, or bypass S2 judgment.
- AC-3.4 WHEN two clones of one repo both contribute a fingerprint, THE SYSTEM SHALL count
  them as one repo (dedup by identity key, US-4), not two.
- AC-3.5 WHEN the aggregator reports a fingerprint, THE SYSTEM SHALL compute
  `distinct_source_harness` (claude-code, codex) and surface the per-harness breakdown, so a
  gap seen on both harnesses (stronger generic evidence) is distinguishable from one
  concentrated on a single harness's adapter.
- AC-3.6 WHEN the aggregator reports cross-repo evidence, THE SYSTEM SHALL report per-repo
  COVERAGE (which enrolled repos exercise the affected surface at all), so a low
  `distinct_repo` on a surface a repo never uses is not read as absence-of-problem
  (absence ≠ absence-of-problem).

### US-4: Identify a repo robustly for tracking and dedup

As a developer, I want a repo identified so the registry survives a move and the count dedups
clones, so identity drift is visible rather than silently miscounting.

Acceptance criteria:

- AC-4.1 WHEN a repo is enrolled, THE SYSTEM SHALL mint a stable local `repo_id` and store it
  with the `path`, used to locate the repo and survive moves.
- AC-4.2 WHEN the aggregator dedups for counting, THE SYSTEM SHALL use an `identity_key` =
  the normalized origin remote URL when present, else the `repo_id`; THE SYSTEM SHALL NOT use
  the path as the identity key (paths overcount clones).
- AC-4.3 WHEN the aggregator records identity, THE SYSTEM SHALL surface the per-fingerprint
  distinct identity keys with display URLs/paths so forks, clones, and domain clusters are
  visible (supports AC-3.2).

### US-5: Consent at the boundary crossing

As a developer, I want to exclude a sensitive repo from even the local aggregate, so a
client or employer repo never enters a cross-repo view, while ordinary repos enroll by
default.

Acceptance criteria:

- AC-5.1 WHEN a repo is bootstrapped/updated, THE SYSTEM SHALL enroll it default-on, because
  the aggregate reads only already-committed data into a view only this developer sees (no new
  trust boundary is crossed).
- AC-5.2 WHEN a developer opts a repo out, THE SYSTEM SHALL record the opt-out **only** in the
  machine-local `~/.foundry/repos.json` and SHALL NOT write an opt-out flag into the repo
  (a committed flag would impose one developer's choice on all clones).
- AC-5.3 WHEN a repo is opted out, THE SYSTEM SHALL exclude it from the aggregate entirely —
  absent, not merely flagged — so its path/remote is not disclosed in the aggregate.
- AC-5.4 WHEN `update` runs on a repo with an existing opt-out, THE SYSTEM SHALL preserve the
  opt-out and SHALL NOT silently re-enroll it.
- AC-5.5 WHEN data would cross the machine boundary (off-host export), THE SYSTEM SHALL treat
  that as a separate, default-off, opt-in, zero-bytes-verified path — out of scope here
  (external-telemetry Backlog).

## Out of scope

- **Off-host / external aggregation** — k-anonymity, pseudonymous install ids,
  `distinct_install`, repo-salted aggregator fingerprints, the off-host export, the
  re-identification eval. Backlog; the machine boundary is the dividing line (AC-5.5).
- **Push / daemon / watcher** — no admission-time second write, no background process, no
  cross-repo writes. Pull-only, on demand.
- **Version comparison** — multi-repo on one machine is still ~all-current; the S1
  no-auto-action rule (loop-signal-store US-7) holds, so `distinct_repo`-as-evidence needs no version ordering.
- **The genericity gate** — overfit remains an S2 judgment; `distinct_repo` is an input to it,
  never a replacement (AC-3.3).
- **S2 ranking / proposal drafting** — this spec produces the cross-repo view S2 reads.
- **Any change to the S1 per-repo schema** — `source_repo` is a read-time annotation (AC-2.7).

## Dependencies

- `loop-signal-store` (S1): the per-repo committed ledger and its repo-independent
  `candidate_fingerprint` (the join key that makes a no-schema-change pull-join possible).
- `.foundry/manifest.json` and the bootstrap/update skills: the enrollment hook that writes
  the user-level registry.
- The broker's append-only / rebuildable-view discipline: the deletable-without-loss invariant
  (AC-2.3) is the broker `rebuild` determinism check applied to the aggregate.
