---
name: code
description: Use when implementing, adding, changing, or fixing a feature in a repo
  with the foundry setup — a board at roadmap/ROADMAP.md, roadmap/specs/, features/ — work that
  ends in a commit. Covers the lifecycle from first design through shipping.
---

# The code lifecycle

This skill defines the ordered stages and gates for feature work in a foundry repo.
Every repo-specific detail comes from:

| Repo specific | Read it from |
|---|---|
| Canonical gate command | `AGENTS.md` Commands (gate inventory: `knowledge/validation.md`) |
| Spec format | `roadmap/specs/README.md` |
| Feature-file conventions | `features/README.md` |
| Vocabulary | `knowledge/glossary.md` |
| The board | `roadmap/ROADMAP.md` |

## The checklist

Copy this into your reply and check off each stage. A gate is a **prohibition**: do
not start a later stage until the prior gate is met.

- [ ] **0 Frame** — classify the work; pick the path below.
- [ ] **1 Spec** — `roadmap/specs/<feature>/{requirements,design,tasks}.md` written + Design reviewed. GATE: no code until the Design is approved.
- [ ] **2 Plan** — bite-sized TDD tasks in `tasks.md`; board card claimed. GATE: no code until the plan is approved.
- [ ] **3 Build** — feature-file Scenario first, then TDD red→green. GATE: new behavior has its Scenario before its code.
- [ ] **4 Verify** — the repo's canonical gate green. GATE: a recorded PASS, pasted — not a claim.
- [ ] **5 Docs** — `python3 scripts/docs.py check` clean; touched docs updated. GATE: no stale or unindexed doc.
- [ ] **6 Finish** — branch first, ask before push, move the card. GATE: `Done` needs the recorded gate PASS.

## 0 · Frame — pick the path

| Work | Path |
|---|---|
| **New feature** | All stages 1 → 6. |
| **Enhancement** of existing behavior | Update the affected Scenario in `features/` + the touched stages; a light spec note, not a full `roadmap/specs/<feature>/`. |
| **Bug fix** | Reproduce → write the failing test → fix → Verify → Finish. Skip 1–2. |
| **Refactor** (no behavior change) | Build → Verify → Finish; leave `features/` untouched. |

## 1 · Spec

Write `roadmap/specs/<feature>/{requirements,design,tasks}.md` in the format `roadmap/specs/README.md`
defines, in the vocabulary of `knowledge/glossary.md`. Before coining any canonical name (glossary term, public type or field, config knob), search the prior art — domain literature, stack naming conventions, comparable tools; record provenance, or why none fits, in the glossary. Dispatch the `spec-reviewer` agent on the Design
before presenting it.
**Gate:** no implementation until the Design is approved.

## 2 · Plan

Break the design into bite-sized TDD tasks in `roadmap/specs/<feature>/tasks.md` — exact
paths, real code, a test per step. Claim the work by setting the owner on its card in
`roadmap/ROADMAP.md` (the board); respect listed dependencies.
**Gate:** no code until the plan exists and is approved.

## 3 · Build

**Feature-file first.** New observable behavior gets a Scenario in `features/`
*before* its implementation; `features/README.md` says which file and contract kind.
Then TDD: red → green. Respect `AGENTS.md` Boundaries. Stage **explicit paths** when
you commit — never `git add -A` (the tree may be shared by parallel agents).
**Gate:** the new behavior has a feature-file Scenario before its code.

## 4 · Verify

Run the repo's canonical gate — the command `AGENTS.md` Commands names.
**Gate:** paste the gate's final PASS line.

## 5 · Docs

Run `python3 scripts/docs.py check` (frontmatter lint) on any new or changed doc.
Update `AGENTS.md` if a convention changed; index a new doc in `knowledge/README.md`.
**Gate:** no finish with a stale or unindexed doc reference.

## 6 · Finish

Branch first if you are on the default branch. **Ask before you commit or push.**
Move the card on `roadmap/ROADMAP.md` Validating → Done. If a real failure showed the
setup let an agent go wrong, write a COE from `knowledge/coe-template.md` — a COE is
closed only by a mechanical change (gate, lint, rule, or eval case), never prose.
**Gate:** `Done` requires the recorded gate PASS.

## Don't rationalize past a gate

| Excuse | Reality |
|---|---|
| "Trivial change — skip the spec." | The bug-fix path still writes a failing test first; acceptance criteria still apply. |
| "I manually checked it; it works." | Not evidence. Run the canonical gate; paste the PASS. |
| "I'll add the Scenario after." | New behavior gets its Scenario first; after-the-fact tests pass vacuously. |
| "`git add -A` is faster." | The tree may be shared; stage explicit paths only. |

Violating the letter of a gate is violating its spirit.

## Enhancement

This skill is the high-level flow. If a more specialized skill fits a stage — design,
planning, testing, debugging, review, finishing — prefer it; it supersedes the method
here. Otherwise the stage's instruction stands.
