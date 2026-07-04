---
name: spec-review
description: Use when reviewing requirements, design, tasks, skills, agents, rules, or other context-resident prose for naming, vocabulary, writing style, token cost, spec-format compliance, or public-surface/invariant completeness before finalization. The interactive spec-stage review; grades against the same rubric the driver's spec gate uses.
---

# Spec Review

Review a spec (or any context-resident prose artifact) against the repo contract. Prefer a
**fresh context** so you grade the artifact, not the author's rationale. Read-only: return
findings; the author applies them.

## The judgment is the spec rubric — fetch it

```
.foundry/bin/foundry rubric spec
```

Fetch it and grade by it: EARS acceptance criteria, the required **Public surface** and
**Invariants** sections, glossary vocabulary and canonical names with provenance, spec-format
compliance (`roadmap/specs/README.md`), and Strunk & White prose. The rubric states the
severity taxonomy (a contract violation is blocking; taste is advisory) and the output
contract — follow both.

For prose that is not a feature spec (a skill, agent, or rule), apply the same naming,
vocabulary, and writing-style judgment; the public-surface/invariant checks are N/A there.

## Output

List findings, most-blocking first: severity, file, one-sentence defect, one-sentence fix.
Then the verdict as the rubric's last line — `SPEC_REVIEW: CLEAN` (no blocking finding
remains) or `SPEC_REVIEW: FINDINGS`.

## Common mistakes

- Do not rewrite the artifact — review only.
- Do not pass on green-ness; grade against the rubric's blocking criteria.
- Do not re-derive judgment here; if the rubric is wrong, fix `src/foundry/rubrics/spec.md`.
