> **Status:** Planned (2026-06-29) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — pr-deliberation

## Summary

A **PR-comment transport** for the cross-family review, so the reviewer and its adversary
converse *visibly* on an open GitHub PR and the human joins inline — instead of the conversation
living in a local `.foundry/reports/` transcript. Run `code-review` against a PR: each `FLAGGED`
finding posts as a review comment anchored to its `file:line`; the cross-family **refuter** replies
KEEP/DROP on each thread; the verdict posts as a PR review (never an auto-approve); the human
replies on any thread and a re-run ingests those replies. It reuses the existing
find → refute → verdict logic and the cross-family machinery — only the *transport* changes
(PR threads, not a report file) — and keeps the refuter's **single asymmetric DROP-only pass**, not
a new agent debate.

## Glossary impact

- **Finding thread** — a PR review-comment thread for one review finding: the reviewer's anchored
  comment, the refuter's KEEP/DROP reply, and any human replies. Prior art: a GitHub PR review
  comment thread. Provenance recorded in `knowledge/glossary.md`.
- **Review transport** — where a review is delivered: the local report (`.foundry/reports/`) or
  the PR (comment threads). Prior art: the transport/adapter distinction — a stable payload over a
  swappable delivery channel; no debt term replaced.

## US-1 — Post the review onto the PR

- AC-1.1 WHEN `code-review` targets an open PR (`code-review --pr <#>`), each `FLAGGED` finding
  SHALL post as a PR review comment anchored to its `file:line`, carrying the finding's severity,
  dimension, evidence, problem, and fix.
- AC-1.2 Each posted comment SHALL be **attributed** to the posting role + harness (e.g. a
  `reviewer (claude)` prefix), because both agents post under the user's one `gh` token.
- AC-1.3 THE verdict SHALL post as a PR review — `CODE_REVIEW: FAIL` → request-changes,
  `PASS` → a comment.
- AC-1.4 THE review SHALL NOT approve the PR (the human approves).

## US-2 — The cross-family refuter replies on the PR (one asymmetric pass)

- AC-2.1 THE cross-family refuter SHALL reply once per finding thread — KEEP (with evidence) or
  DROP (with reason), attributed to the refuter harness — reusing the existing **single
  asymmetric, DROP-only** discipline (it removes a finding, never adds one; not a debate).
- AC-2.2 A DROP SHALL exclude that finding from the verdict (recall-monotone-down).
- AC-2.3 WHEN the repo is single-harness (no complementary family), the refuter SHALL be skipped
  and the reviewer runs single-agent, as today.

## US-3 — Human-in-the-loop, turn-based

- AC-3.1 WHEN a finding thread carries a human "won't fix" / "intended" reply, THE re-run SHALL
  resolve the thread and drop the finding from the verdict.
- AC-3.2 WHEN a finding thread carries a human question, THE re-run SHALL post exactly one reply.
- AC-3.3 THE deliberation SHALL be bounded: per run, the reviewer posts once, the refuter replies
  once per thread, the verdict posts once — no agent-vs-agent loop. The human's async replies drive
  the next run (turn-based, not real-time).

## US-4 — Idempotent, bounded re-runs

- AC-4.1 A re-run SHALL match a finding to its existing thread by `file:line` + normalized
  signature and SHALL NOT post a duplicate comment.
- AC-4.2 WHEN a finding no longer appears (fixed) or was human-resolved, the re-run SHALL resolve
  its thread.
- AC-4.3 One finding maps to one thread; the refuter posts at most one reply per thread per run
  (the comment-noise bound).

## US-5 — Eval (deterministic; live deferred)

- AC-5.1 A hermetic test (a mock `gh` seam) SHALL prove: a `FLAGGED` finding maps to one anchored
  comment; a DROP'd finding is excluded from the verdict; a re-run with the same findings posts no
  duplicate (idempotent); a human "won't fix" reply drops the finding; a human question yields
  exactly one reply; the verdict never approves. The live PR run ships deferred.

## Metrics

- A `FLAGGED` finding becomes one anchored PR comment; a DROP'd finding never reaches the verdict;
  a re-run posts zero duplicate comments — asserted by the mock-`gh` test.
- The verdict is a comment / request-changes; the PR is never auto-approved.
