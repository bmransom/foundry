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
4. Read the report, apply accepted fixes, and re-run if the fixes change names,
   vocabulary, requirements, design, tasks, skills, agents, or rules.

If fresh context is unavailable, review inline and say so before findings.

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

Return a findings list grouped by file. Each finding must include location, problem,
and concrete fix. Note clean files briefly. End with the single highest-priority fix.
