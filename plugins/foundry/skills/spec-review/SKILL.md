---
name: spec-review
description: Use when reviewing requirements, design, tasks, skills, agents, rules, or other context-resident prose for naming, vocabulary, writing style, token cost, or spec wording before finalization.
---

# Spec Review

Review naming and prose against the repo contract. Prefer a fresh context so the
reviewer sees the artifact, not the author's rationale.

## Fresh-context workflow

1. Identify the target files.
2. Run `scripts/spawn-spec-reviewer.sh <target> [repo-dir]` when tmux is available.
   The wrapper delegates to Foundry's shared fresh-session runner.
3. Wait for the report in `.foundry/reports/spec-review/`.
4. Read the report, apply accepted fixes, and re-review. The re-pass is **blind** —
   spawn a fresh reviewer on the current artifact; never hand it a summary of your
   changes (a judge told what changed verifies instead of re-scrutinizing).

If fresh context is unavailable, review inline and say so. Never run a **primed** re-pass
inline: if you cannot spawn a fresh reviewer for round 2+, hold the gate rather than let
your account of the edits replace an independent pass.

## Contract

Read these before reviewing:

- `knowledge/glossary.md` for canonical terms, debt terms, and entity model.
- The `AGENTS.md` "Writing style" section for prose standards.

If either file is missing, note that and review against the contract that exists.

## Flag

**Names**

- A concept with a canonical glossary term that uses another word.
- Any term the glossary marks as debt.
- Public types, fields, metrics, config, files, or directories that conflict with
  the glossary's entity model.
- Near-duplicate names that invite confusion.
- New canonical terms without prior art or a reason prior art does not fit.

**Prose**

- Needless words, hedges, qualifiers, passive voice, or vague phrasing.
- A buried point that should lead the sentence.
- A paragraph a list, table, or command would carry better.
- Context-resident prose that spends tokens without changing behavior.

Flag only contract violations. Do not redesign the feature, expand scope, or impose
preferences not present in the repo contract.

## Output

Return a findings list grouped by file. Each finding includes location, problem,
**severity** — `blocking` or `advisory` — and a concrete fix. Emit a
`FLAGGED: <short signature>` line for **each blocking finding** (the convergence loop and
`score_review.py` read these); list advisory findings separately, without `FLAGGED:` lines.
Note clean files briefly, then the highest-priority blocking fix.

Classify severity: a **contract violation** — a wrong canonical name, a debt term used for
its concept, an entity-model conflict, missing provenance, a spec-format breach, or an
internal inconsistency — is `blocking`; a taste-level **prose** preference is `advisory`.
Objective **banned filler phrases** are enforced by `prose-lint.py` in the gate, not flagged
here; contextual debt-term misuse stays a judge call (the glossary scopes debt terms by
context, so it is not lintable).

End with a final verdict line — the **last line** of the report — exactly one of:

- `SPEC_REVIEW: CLEAN` — no unresolved `blocking` finding remains (advisory may remain).
- `SPEC_REVIEW: FINDINGS` — one or more `blocking` findings above.

This verdict is the loop's deterministic stop token: it re-reviews (blind) after each edit
until no `blocking` finding remains. Emit the verdict on every review.
