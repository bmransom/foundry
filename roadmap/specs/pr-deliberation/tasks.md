> **Status:** Planned (2026-06-29) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — pr-deliberation

## Wave 1 — the PR transport

- T1 `plugins/foundry/scripts/pr-review-transport.sh`: given the reviewer's `FLAGGED` findings (+
  bodies), the refuter's KEEP/DROP, and the PR number, post each new finding as a review comment
  anchored to its `file:line` (attributed `reviewer (<family>)`), reply the refuter's KEEP/DROP per
  thread (attributed `refuter (<family>)`), and compute the surviving blocking set. Read existing
  threads via `gh` (the `GH_CMD` seam) to dedupe by `file:line` + a `footer-algebra.sh signature`
  (a new subcommand reusing the existing `normalize`, so the dedupe key has one source of truth)
  (AC-1.1, AC-1.2, AC-2.1, AC-2.2, AC-4.1, AC-4.3).
- T2 Verdict + human replies: post the verdict as `gh pr review` — `FAIL`→request-changes,
  `PASS`→comment, **never approve** (AC-1.3, AC-1.4); read thread replies and act — a
  "won't fix"/"intended" resolves the thread + drops the finding (AC-3.1), a question gets exactly
  one reply (AC-3.2); resolve a thread whose finding is gone (AC-4.2).
- Gate: `tests/pr_review_transport_test.sh` (mock `gh`) — anchored comments, DROP excluded from the
  verdict, idempotent re-run, "won't fix" drops, verdict never approves (AC-5.1).

## Wave 2 — wire into code-review

- T3 `plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh` + `SKILL.md`: a `--pr <#>`
  mode — run the reviewer + the cross-family refuter (single asymmetric pass, skip on single-family:
  AC-2.3) as today, then deliver via `pr-review-transport.sh` instead of `.foundry/reports/`. Bound
  the deliberation to one run (no loop: AC-3.3). Keep `SKILL.md` within budget.
- Gate: `code_review_cycle_test` + the transport test pass; the local (non-`--pr`) path unchanged.

## Wave 3 — knowledge

- T4 `knowledge/glossary.md`: add `Finding thread` and `Review transport` with provenance;
  `knowledge/log.md` records the feature. Confirm the live PR run is deferred (a `Validating`
  post-merge check), not a gate blocker.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; `knowledge.py check` clean.
