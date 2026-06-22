> **Status:** Ready (2026-06-21) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — local multi-repo aggregate

Waves run top to bottom; tasks within a wave are parallel unless they name a dependency.
Test-first: the gate is the test that proves it. Depends on `loop-signal-store` (S1) — the
per-repo committed ledger and its repo-independent `candidate_fingerprint` (the join key).

## Wave 0 — Spec, board, glossary

- [ ] T1: Land the spec files + board card — `roadmap/specs/local-multirepo-aggregate/{requirements,design,tasks}.md`, `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` PASS. [US-1]
- [ ] T2: Pre-approval `spec-review` in fresh context; apply findings. Gate: no findings, or each dispositioned + fixed. [Spec README]
- [ ] T3: Glossary provenance for the new terms — `repo registry`, `repo_id`/`identity_key`, `distinct_repo`, `distinct_source_harness`, `source list`, `coverage`, `machine-local aggregate`, the boundary-crossing consent rule. Gate: `spec-review` raises no un-provenanced canonical name. [US-4, US-5]

## Wave 1 — Registry + enrollment

- [ ] T4: Add `tests/loop_multirepo_registry_test.sh` — enrolling a repo writes `~/.foundry/repos.json` with `repo_id` + `path` + `remotes[]` + `enrolled`; a move refreshes `path` without changing `repo_id`; `update` preserves an existing opt-out; an opted-out repo is absent (not flagged); no ambient filesystem discovery. Seeded-defect arm: a mutant that re-enrolls an opted-out repo fails. Gate: fails before, passes after T5/T6. [AC-1.1–1.3, AC-5.1–5.4]
- [ ] T5: Implement the registry reader/writer (mint stable `repo_id`, upsert `path`/`remotes[]`, machine-local opt-out) (dep T4). Gate: registry assertions PASS. [AC-1.1–1.3, AC-4.1, AC-5.2–5.4]
- [ ] T6: Add the enrollment hook to the bootstrap + update skills (default-on upsert, preserve opt-out) (dep T5). Gate: bootstrap/update on a repo enrolls it; opt-out survives update. [AC-1.2, AC-5.1, AC-5.4]

## Wave 2 — Pull aggregator + identity + provenance

- [ ] T7: Add `tests/loop_multirepo_aggregate_test.sh` against fixture repos with seeded S1 ledgers — group by `candidate_fingerprint`; `distinct_repo` = distinct `identity_key`s; clone dedup (two clones of one origin count once); `identity_key` = normalized origin URL else `repo_id`, never path; scan metadata stamped (HEAD, dirty, ledger-hash); missing/moved/invalid repo skipped-with-reason; per-repo S1 ledger emits no `source_repo`. Seeded-defect arms: path-as-identity → clone overcount fails; a crash-on-missing-repo mutant fails; a mutant writing `source_repo` to a per-repo ledger fails. Gate: fails before, passes after T8. [AC-2.1–2.7, AC-3.1, AC-3.4, AC-4.1–4.3]
- [ ] T8: Implement `plugins/foundry/scripts/loop-multirepo-aggregate.py` — harden the spike `aggregate.py`: registry scan, read-only ledger read, hybrid identity, `source_repo` read-time annotation, scan provenance, skip-with-reason (dep T7). Gate: T7 PASS. [AC-2.1–2.7, AC-3.1, AC-3.4, AC-4.1–4.3]

## Wave 3 — Cross-repo view: evidence-not-a-gate, harness breakdown, coverage

- [ ] T9: Extend the aggregator test with the **keystone evidence-not-a-gate** arm — a mutant that auto-resolves/auto-admits a candidate on `distinct_repo >= 2` (bypassing S2) must fail; the count always ships with its source list; `distinct_source_harness` per-harness breakdown computed; per-repo coverage reported (absence ≠ absence-of-problem); a fingerprint-collision surfaces with its source list and no auto-promotion (dep T8). Gate: each seeded defect fails its guard. [AC-3.2, AC-3.3, AC-3.5, AC-3.6]
- [ ] T10: Implement the cross-repo view render — `view.jsonl` + rebuildable `aggregate.md` carrying `distinct_repo`, `distinct_source_harness` + breakdown, the source list, coverage, scan metadata; the count never rendered bare (dep T9). Gate: T9 PASS. [AC-3.1–3.6]

## Wave 4 — Rebuildable-view determinism + finish

- [ ] T11: Add the rebuildable-view arm — delete `~/.foundry/aggregate/`, rebuild from the same inputs, assert byte-identical; a mutant storing state only in the aggregate (lost on delete) fails. Implement the determinism check (dep T10). Gate: delete+rebuild byte-identical; the shadow-truth mutant fails. [AC-2.3]
- [ ] T12: Re-run `spec-review`; apply findings. Run the canonical gate. Gate: `scripts/check-fast.sh` prints `check-fast: PASS` with the registry, aggregator, evidence-not-a-gate, and rebuild tests landed. [Spec README, US-1]
