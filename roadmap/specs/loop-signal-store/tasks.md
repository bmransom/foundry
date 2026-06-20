> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — loop signal store (S1)

Waves run top to bottom. Tasks within a wave are parallel unless they name a
dependency. Each task is written test-first: the gate is the test that proves it,
and the test must fail before the change and pass after.

## Wave 1 — Spec and board

- [ ] T1: Add the `loop-signal-store` spec files and board card —
  `roadmap/specs/loop-signal-store/{requirements,design,tasks}.md`,
  `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` PASS after the spec files and
  board card land. Approval: maintainer approval recorded on the board. [US-1]
- [ ] T2: Run pre-approval `spec-review` on requirements, design, and tasks in fresh
  context; apply findings before asking for design approval. Gate: review report has
  no findings, or every finding has a recorded disposition and fix. [Spec README]
- [ ] T3: Confirm the loop-signal-store terms' glossary provenance — Signal,
  Candidate, Metric, Candidate ledger, Redaction gate carry prior-art provenance in
  `knowledge/glossary.md` (added when this spec landed) and the three spec files use
  them consistently. Gate: `spec-review` (or the glossary contract) raises no
  un-provenanced canonical name across the three spec files. [US-3, US-5]

## Wave 2 — Append-only store mechanics (depends: `AppendOnlyStore` extraction, see design Dependencies)

- [ ] T4: Add `tests/loop_signal_store_test.sh` against a temp store dir, modeled on
  `tests/harness_deliberation_snapshot_test.sh`. Assert: an appended event gets a
  monotonic id; a rewrite is refused; a payload rewritten with different bytes is
  refused; a rebuild re-validates payload hashes and refuses on view drift; an
  unknown event type is rejected at append and rebuild. Add a seeded-defect arm: a
  mutant store that mutates an existing event passes only if discrimination fails.
  Gate: the test fails against an empty/stub store and the mutant arm flags the
  seeded defect. [AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5]
- [ ] T5: Implement the store's append-only / immutable-payload / rebuildable-view
  mechanics and the closed loop event set in
  `plugins/foundry/scripts/loop-signal-store.py`, built on storage mechanics copied
  from the broker's `SessionStore` (the `AppendOnlyStore` base lands separately; this
  task starts on copied mechanics) (dep T4). Gate: `tests/loop_signal_store_test.sh`
  PASS for the storage assertions. [AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5]

## Wave 3 — Two-zone storage and the store header

- [ ] T6: Extend `tests/loop_signal_store_test.sh` with zone-separation assertions —
  raw payloads land under `.foundry/tmp/self-improvement/`, the committed ledger
  lands under `.foundry/state/self-improvement/`, no raw signal text lands in the
  committed zone — and the `store_started` event records repo root and schema
  version. Add a seeded-defect arm: a mutant store that writes raw payload bytes into
  `.foundry/state/` makes the test fail (dep T5). Gate: the test fails against the
  current store and the mutant arm flags the seeded defect. [AC-1.1, AC-1.2,
  AC-1.2b, AC-1.3, AC-1.4]
- [ ] T7: Implement the two-zone split in the store — a raw writer targeting
  `.foundry/tmp/self-improvement/` by SHA-256 and a committed writer targeting
  `.foundry/state/self-improvement/` — and emit `store_started` on init (dep T6).
  Gate: the T6 zone-separation assertions PASS; no raw text reaches the committed
  zone. [AC-1.1, AC-1.2, AC-1.2b, AC-1.3, AC-1.4]

## Wave 4 — Redaction gate and its discriminating eval

- [ ] T8: Add `evals/fixtures/redaction-gate/` and `evals/harness/redaction-gate-eval.sh`
  — seed a committed-bound summary carrying a planted raw-leak (an absolute path, a
  secret token, a PII string) plus clean decoys; the eval fails if any planted leak
  passes the gate or if a clean decoy is wrongly rejected. Gate: the eval fails
  against a no-op gate (every seeded leak passes) — discrimination, not green-ness.
  [AC-4.1, AC-4.2, AC-4.3, AC-4.7]
- [ ] T9: Implement the redaction gate as the single committed-zone writer in
  `loop-signal-store.py` — reject on a raw-text marker (path / secret / PII) and on
  duplicate / overfit / private / out-of-scope, write nothing to `.foundry/state/`
  on rejection, and record `signal_rejected` naming the marker class or reason
  (never the matched raw text) (dep T8). Gate: `evals/harness/redaction-gate-eval.sh`
  PASS — every planted leak is rejected, every clean decoy passes. [AC-4.1, AC-4.2,
  AC-4.3, AC-4.4, AC-4.5, AC-4.6, AC-4.7]

## Wave 5 — Signal ingest and metric observation

- [ ] T10: Extend `tests/loop_signal_store_test.sh` with ingest assertions — a
  `signal_ingested` event carries `source_kind`, a hash-ref to the raw payload, and a
  generic summary; an unrecognized `source_kind` is rejected; a `metric_observed`
  event carries the `score_review.py` summary fields — `fixture`, `runs`,
  `mean_recall`, `decoy_hits`, `verdict`; the `telemetry` seam value ingests with no
  schema change beyond the `source_kind` value. Add a seeded-defect
  arm: ingest with `source_kind` outside the closed set must be rejected (dep T7,
  T9). Gate: the test fails against the current store and the mutant arm flags the
  seeded defect. [AC-3.1, AC-3.2, AC-3.3, AC-3.4]
- [ ] T11: Implement signal ingest and metric observation in `loop-signal-store.py` —
  route every signal through the raw writer then the redaction gate, record
  `signal_ingested` with the closed `source_kind` set, and record `metric_observed`
  in the `score_review.py` shape (dep T10). Gate: the T10 ingest assertions PASS,
  including `source_kind` rejection and the metric shape. [AC-3.1, AC-3.2, AC-3.3,
  AC-3.4]

## Wave 6 — Candidate aggregation and the read seam

- [ ] T12: Extend `tests/loop_signal_store_test.sh` with aggregation assertions — a
  `candidate_opened` event fingerprints on
  `source_kind + invariant + failing_signature + affected_surface`; a second signal
  matching that fingerprint folds in via `candidate_revised` (no duplicate
  candidate); a candidate record carries every field in AC-5.3; `candidate_closed`
  names a resolution; `ledger.md` rebuilds from the events alone. Add a seeded-defect
  arm: a duplicate-opening mutant (ignores the fingerprint match) makes the test fail
  (dep T11). Gate: the test fails against the current store and the mutant arm flags
  the seeded defect. [AC-5.1, AC-5.2, AC-5.3, AC-5.4, AC-5.5]
- [ ] T13: Implement candidate aggregation and the rebuildable ledger view in
  `loop-signal-store.py` — fingerprint normalized causes, fold matches via
  `candidate_revised`, carry every AC-5.3 field, close on resolution, and render
  `ledger.md` from the events (dep T12). Gate: the T12 aggregation assertions PASS,
  including no-duplicate folding and the ledger rebuild. [AC-5.1, AC-5.2, AC-5.3,
  AC-5.4, AC-5.5]
- [ ] T14: Add a read-seam test — the committed view exposes active candidates and
  metric trends without parsing raw payloads, and a fresh clone with no
  `.foundry/tmp/` zone still exposes the committed ledger (simulate by removing the
  raw zone and re-reading) (dep T13). Gate: the read-seam test PASS — candidates
  resolve from `.foundry/state/` alone. [AC-6.1, AC-6.2, AC-6.3]

## Wave 7 — Review and finish

- [ ] T15: Re-run `spec-review` on requirements, design, and tasks after any
  implementation-driven spec changes; apply findings. Gate: review report has no
  findings, or every finding has a recorded disposition and fix. [Spec README]
- [ ] T16: Run the canonical gate. Gate: `scripts/check-fast.sh` prints
  `check-fast: PASS` with the store test, the redaction-gate eval, and the
  glossary terms landed. [US-1, T1]
