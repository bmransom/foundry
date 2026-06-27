---
name: code
description: "Use when implementing, adding, changing, or fixing a feature in a repo with the foundry setup: roadmap/ROADMAP.md, roadmap/specs/, features/, knowledge/, and work that ends in verification or a commit. Covers the lifecycle from design through shipping."
---

# The code lifecycle

The high-level dispatcher for feature work in a foundry repo. Keep repo facts in
`AGENTS.md`, `rules/`, and the knowledge base; defer judgment-heavy checks to
lower-level skills so this lifecycle stays small. When a specialized skill fits a
stage, prefer it — it supersedes the method here; otherwise the stage's instruction stands.

Every repo-specific detail comes from:

| Repo specific | Read it from |
|---|---|
| Canonical gate command | `AGENTS.md` Commands (gate inventory: `knowledge/validation.md`) |
| Spec format | `roadmap/specs/README.md` |
| Feature-file conventions | `features/README.md` |
| Vocabulary | `knowledge/glossary.md` |
| The board | `roadmap/ROADMAP.md` |

**Precondition.** If there is no `AGENTS.md` or `roadmap/ROADMAP.md`, stop and
point the user to the bootstrap skill rather than writing foundry files.

## The checklist

Copy this into your reply and check off each stage. A gate is a **prohibition**: do
not start a later stage until the prior gate is met.

- [ ] **0 Frame** — classify the work; pick the path below.
- [ ] **1 Spec** — `roadmap/specs/<feature>/{requirements,design,tasks}.md` written, reviewed, and revised. GATE: no code until Design is approved.
- [ ] **2 Plan** — bite-sized TDD tasks in `tasks.md`; board card claimed. GATE: no code until the plan is approved.
- [ ] **3 Build** — feature-file Scenario first, then TDD red→green. GATE: new behavior has its Scenario before its code.
- [ ] **4 Verify** — the repo's canonical gate green. GATE: a recorded PASS, pasted — not a claim.
- [ ] **5 Knowledge** — `python3 scripts/knowledge.py check` clean; touched concepts updated. GATE: no stale concept or `index.md`.
- [ ] **6 Review** — `code-review` in fresh context; fix every blocking finding. GATE: no commit or PR with an unresolved blocking finding.
- [ ] **7 Finish** — branch first, ask before push, move the card. GATE: `Done` needs the recorded gate PASS.

## 0 · Frame — pick the path

| Work | Path |
|---|---|
| **New feature** | All stages 1 → 7. |
| **Enhancement** of existing behavior | Update the affected Scenario in `features/` + the touched stages; a light spec note, not a full `roadmap/specs/<feature>/`. |
| **Performance-sensitive change** | Use `performance` during Spec/Plan/Verify, then follow the matching feature, enhancement, bug-fix, or refactor path. |
| **Naming, API, or vocabulary change** | Use `naming-standards` during Spec/Plan before writing public names. |
| **New boundary, extension point, or interaction model** | Use `design-patterns` and `modular-structure` during Spec/Plan. |
| **Bug fix** | Reproduce → write the failing test → fix → Verify → Finish. Skip 1–2. |
| **Refactor** (no behavior change) | Build → Verify → Finish; leave `features/` untouched. |

## 1 · Spec

Write `roadmap/specs/<feature>/{requirements,design,tasks}.md` in the format
`roadmap/specs/README.md` defines and the vocabulary of `knowledge/glossary.md`.
Consider all five skills below for every feature — apply each, or note **N/A** with a reason. Name the metrics that tell whether the feature works, or N/A. Never skip silently; re-loop on any spec or vocabulary change:

1. Use `spec-review` in fresh context (requirements, design, tasks) — the spec-convergence loop: re-review after each edit until `SPEC_REVIEW: CLEAN`, cap 10; at the cap, surface remaining `FLAGGED:` findings and hold the Design gate.
2. Use `naming-standards` for new glossary terms, public APIs, config, metrics, files, and directories.
3. Use `design-patterns` for boundaries, extension points, eventing, adapters, construction, and algorithm selection.
4. Use `modular-structure` for placement, bounded contexts, dependency direction, public/internal APIs, and directory shape.
5. Use `performance` for hot paths, resource use, model/tool calls, and user-visible latency.

**Gate:** no implementation until the Design is approved.

## 2 · Plan

Break the design into bite-sized TDD tasks in `roadmap/specs/<feature>/tasks.md` — exact
paths, real code, a test per step. Claim the card in `roadmap/ROADMAP.md` by setting the
owner, the branch, and any out-of-repo worktree path; respect listed dependencies.
For performance-sensitive work, include the baseline plan from `performance` before
code (main vs feature, flag-off vs flag-on, old vs new), naming the workload and correctness gate.
**Gate:** no code until the plan exists and is approved.

## 3 · Build

**Feature-file first.** New observable behavior gets a Scenario in `features/`
*before* its implementation (`features/README.md` says which file and contract kind);
then TDD red → green. Respect `AGENTS.md` Boundaries. Stage **explicit paths** when you
commit — never `git add -A` (the tree may be shared by parallel agents).
**Gate:** the new behavior has a feature-file Scenario before its code.

## 4 · Verify

Run the repo's canonical gate — the command `AGENTS.md` Commands names.
**Gate:** paste the gate's final PASS line.

## 5 · Knowledge

Run `python3 scripts/knowledge.py check` on any new or changed concept, regenerate the
listing (`python3 scripts/knowledge.py index`), and log the change in `knowledge/log.md`.
Update `AGENTS.md` if a convention changed.
**Gate:** no finish with a stale concept or `index.md`.

## 6 · Review

Run Review as the bounded **outer fix-convergence loop** (`code-review-convergence-hook.sh`): each round
runs one converged `code-review` in fresh context. **PASS** clears it; **FAIL** surfaces blocking findings
*you* fix via the SDLC, then re-review (the reviewer never fixes). Advisory findings permit Finish; a
docs/knowledge finding loops to **Knowledge** first. After the **20-round** ceiling, escalate — never
auto-pass. Mechanics: code-review's `references/convergence.md`. **Gate:** no unresolved blocking finding ships.

## 7 · Finish

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
