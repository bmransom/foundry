> **Status:** Ready (2026-06-21) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — loop signal store (S1)

Waves run top to bottom; tasks within a wave are parallel unless they name a dependency.
Each task is test-first: the gate is the test that proves it, and the test must fail before
the change and pass after. Wave 1 is the **vertical slice** — the smallest end-to-end proof,
on a skill we own, before breadth.

## Wave 0 — Spec, board, glossary

- [ ] T1: Land the revised spec files + board card — `roadmap/specs/loop-signal-store/{requirements,design,tasks}.md`, `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` PASS. [US-1]
- [ ] T2: Pre-approval `spec-review` on the three files in fresh context; apply findings. Gate: review report has no findings, or each has a recorded disposition + fix. [Spec README]
- [ ] T3: Glossary provenance for the loop terms — `Candidate`, `Candidate ledger`, `Redaction gate`, `Store write lock`, `affected_surface`, `failure_mode`, `source_kind`/`source_harness`, `root conversation`, `recency window`, `candidate decision`, `loop_generated`/`origin_chain`, the telemetry opt-in gate. **Reconcile the drifted glossary entries** — `Candidate` fingerprint inputs → `(affected_surface, failure_mode)`; `Metric` → mark `metric_observed` deferred (not a v1 event); `Redaction gate` → trim to free-text/path/secret/PII (overfit → S2, dedup → fingerprint-fold). Gate: `spec-review` raises no un-provenanced or drifted canonical name. [US-6]

## Wave 1 — Vertical slice (broker `participant_failed` → S1 candidate)

- [ ] T4: Add `tests/loop_signal_store_slice_test.sh` — drive a minimal store: append `store_started` + a `candidate_observed` from a synthetic broker `participant_failed` (`source_kind=dogfood`, `source_harness=claude-code`, `affected_surface=harness-deliberation`, `failure_mode=per-turn-budget-exceeded`); assert the candidate view surfaces it. Seeded-defect arm: a mutant that drops the observation surfaces nothing → fail. Gate: the test fails against an empty store and passes once the slice lands. [US-9 AC-9.1, US-2]
- [ ] T5: Minimal store in `plugins/foundry/scripts/loop-signal-store.py` — append-only `events.jsonl`, the closed v1 event set, an `observe` entrypoint, and a minimal candidate view (dep T4). Gate: T4 PASS. [AC-2.1, AC-2.5, AC-9.1]
- [ ] T6: Instrument `harness-deliberation-broker.py` to call `loop-signal-store observe …` on `participant_failed`, mapping the failure detail to the closed `failure_mode` enum (Tier 1, deterministic) (dep T5). Gate: a broker `participant_failed` (the recorded budget-cap failures) produces a `candidate_observed`; the candidate view names the budget-cap gap. [AC-9.1, AC-5.6]

## Wave 2 — Full store mechanics + two-zone split

- [ ] T7: Extend the store test — append-only monotonic ids, rewrite refused, immutable-payload (differing bytes refused), rebuild re-validates hashes + refuses on view drift, unknown event type rejected; zone separation (raw under `.foundry/tmp/self-improvement/`, committed under `.foundry/state/self-improvement/`, no raw text committed). Seeded-defect arm: a mutant writing raw bytes to `.foundry/state/` fails (dep T5). Gate: fails against the minimal store, passes after T8. [AC-1.1–1.4, AC-2.1–2.4]
- [ ] T8: Implement the two-zone split + full append-only/immutable/rebuildable mechanics (copied broker `SessionStore` mechanics; rebase onto `AppendOnlyStore` when it lands) (dep T7). Gate: T7 PASS. [AC-1.1–1.4, AC-2.1–2.4]

## Wave 3 — Closed schema + redaction gate

- [ ] T9: Add `evals/harness/redaction-gate-eval.sh` + `evals/fixtures/redaction-gate/` — seed a committed-bound record with a planted path, secret, PII, and a free-text field, plus clean decoys; the eval fails if any planted leak passes OR a clean decoy is wrongly rejected. Gate: fails against a no-op gate (discrimination). [AC-4.1–4.5]
- [ ] T10: Implement the redaction gate as the single committed-zone writer + closed-schema validation (reject any free-text field) (dep T9). Gate: redaction eval PASS. [AC-4.1–4.5]

## Wave 4 — Fingerprint canonicalization + closed enums

- [ ] T11: Add a fingerprint test — two divergent free-form cause descriptions classified to the same `(affected_surface, failure_mode)` tuple yield one fingerprint; two distinct tuples do not collide; an unknown surface/failure_mode is rejected; `fingerprint_version` stamped. Seeded-defect arm: a mutant hashing agent free-form text produces two fingerprints for one cause → fail. Gate: fails before, passes after T12. [AC-6.1, AC-6.3, AC-6.5]
- [ ] T12: Implement the fingerprint canonicalizer (`sha256` of the canonical closed tuple, excluding raw text/paths/ids) + the closed `affected_surface` and per-surface `failure_mode` enums; stamp the AC-4.6 closed-schema fields on `candidate_observed` (`build_kind`/`build_label` never compared, `convention_version` stamped-not-gated, `fingerprint_version`, `origin`/`origin_chain`) (dep T11). Gate: T11 PASS and a `candidate_observed` carries every AC-4.6 field. [AC-4.6, AC-6.1–6.5]

## Wave 5 — Conversation recurrence, computed liveness, decision

- [ ] T13: Add a recurrence/liveness test — distinct `root_conversation_id` counting (retries/children fold to root, don't inflate), the recency window, `live`/`quiet`/`regression-suspected` computed from the stream, one `candidate_decision` collapses resolution, a post-decision observation flags `for_review` (never auto-acts). Seeded-defect arm: a mutant counting raw occurrences inflates the bar → fail. Gate: fails before, passes after T14. [AC-5.1–5.4, AC-7.1–7.5]
- [ ] T14: Implement conversation identity (adapter-stamped `conversation_id`/`root_conversation_id`, agent-supplied rejected), the recency window, computed liveness/regression, and `candidate_decision` (dep T13). Gate: T13 PASS. [AC-5.1–5.4, AC-7.1–7.5]
- [ ] T14a: Add a quarantine-scope test — a `loop_generated` design-output candidate is quarantined; an operational failure inside the loop is captured (not quarantined). Gate: a mutant that quarantines operational failures fails. [AC-5.5, AC-5.6]

## Wave 6 — Tier-2 capture (Stop-hook narrower + scope-filter)

- [ ] T15: Harden `.foundry/tmp/loop-dryrun/capture_hook.py` into the Tier-2 narrower — grep closed marker-set + proximity, fold to `root_conversation_id`, surface top-N spans relative-not-absolute. Test: high recall on known-signal fixtures, pure-domain fixtures suppressed. Gate: a mutant using raw failure-grep (no proximity) floods false spans → fail. [AC-9.2, AC-9.4]
- [ ] T16: Wire the Stop-hook entrypoint + the agent scope-filter contract (foundry-mechanism vs repo-domain, distinct from the genericity gate) feeding `observe` (dep T15). Gate: a domain-only transcript yields no `candidate_observed`; a foundry-gap transcript does. [AC-9.2, AC-9.3]

## Wave 7 — Concurrency, telemetry gate, read seam

- [ ] T17: Add the discriminating concurrency arm — N writers (shared + distinct fingerprints, a payload over the atomic-append size), assert no torn line, one candidate per fingerprint, lock-free reads, consistent rebuild; a lock-dropped mutant fails. Then implement the advisory `flock` write critical section + atomic view writes (dep T8, T14). Gate: the arm PASS, the lock-dropped mutant fails. [AC-2b.1–2b.7]
- [ ] T18: Add the telemetry opt-in gate test (off ⇒ `signal_rejected` `telemetry-disabled`, nothing else written; on ⇒ admits; internal sources unaffected; positive control) + implement it ahead of redaction, reading `.foundry/self-improvement-config.json` (absent ⇒ OFF) (dep T10). Gate: the test PASS including the positive control. [AC-3.5–3.7]
- [ ] T19: Add a read-seam test — the committed view exposes live candidates + the per-`source_harness` breakdown without parsing raw payloads; a fresh clone with no raw zone still exposes the ledger. Implement the read seam (dep T14). Gate: the test PASS. [AC-8.1–8.5]

## Wave 8 — Review and finish

- [ ] T20: Re-run `spec-review` after implementation-driven spec changes; apply findings. Gate: no findings, or each dispositioned + fixed. [Spec README]
- [ ] T21: Run the canonical gate. Gate: `scripts/check-fast.sh` prints `check-fast: PASS` with the store test, the redaction-gate eval, the fingerprint eval, and the glossary terms landed. [US-1, T1]
