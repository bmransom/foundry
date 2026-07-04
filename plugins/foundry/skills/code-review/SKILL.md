---
name: code-review
description: Use when reviewing an implementation diff against its spec before Finish — grading lifecycle evidence, complete implementation, docs/knowledge sync, domain language, logging, simplicity, interfaces, structure, efficiency, defaults, and test discrimination from artifacts, never self-claims. The interactive review-stage skill; grades against the same rubric the driver's review gate uses.
---

# Code Review

Review a change against its spec and the repo contract. **Read-only**: return findings,
never edit the code under review. Prefer a **fresh context** so you grade the diff, not the
author's rationale.

This is the interactive, against-spec review. It differs from the generic `/code-review`
(bug/quality sweep of the working tree) and from `.foundry/bin/foundry review <pr>` (the
driver's headless, adversarially-verified PR review) — use this when you want the spec-graded
review in the session you're working in.

## The judgment is the review rubric — fetch it

```
.foundry/bin/foundry rubric review
```

Fetch it and grade by it: lifecycle evidence over self-claims, complete implementation
against the spec's acceptance criteria, docs/knowledge sync, domain language, logging,
simplicity, interfaces, structure, efficiency, defaults, and test discrimination. The rubric
states the severity taxonomy and the output contract — follow both.

Verify suspicions before reporting: read the code, run the test, reproduce the failing case.
A finding you could not reproduce is a question, not a defect.

## Output

List findings, most-severe first: severity, file:line, one-sentence defect, the failure
scenario. Then the verdict as the rubric's last line — `CODE_REVIEW: PASS` (no unresolved
blocking finding) or `CODE_REVIEW: FAIL`.

## Common mistakes

- Do not fix — the author applies findings, then re-reviews.
- Do not grade on green tests alone; a test that does not discriminate is a finding.
- Do not re-derive judgment here; if the rubric is wrong, fix `src/foundry/rubrics/review.md`.
