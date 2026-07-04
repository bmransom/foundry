---
name: code
description: Use when implementing, adding, changing, or fixing a feature in a foundry-bootstrapped repo (roadmap/ROADMAP.md, roadmap/specs/, features/, .foundry/) and you want to drive it through the lifecycle in THIS session — spec, plan, build, verify, knowledge, review, finish — supervised, sharing the conversation you're already in. Invoke by name to pair on a card; the interactive twin of the headless `.foundry/bin/foundry run <card-id>`. Covers the arc from design through shipping.
---

# The code lifecycle (supervised)

Drive one card through the foundry lifecycle in this session. The current agent — the one
you're talking to — does the work, keeping the context you've already built together. The
judgment at each stage is not written here: fetch it from the same rubrics the deterministic
driver compiles, so the supervised walk and an autonomous run grade by one standard.

For an unattended, ledgered run that spawns a fresh session per stage, use
`.foundry/bin/foundry run <card-id>` instead. Reach for this skill when you want to stay in
the conversation, not hand it off.

## The judgment lives in the rubrics — fetch, don't reinvent

```
.foundry/bin/foundry rubric            # the ordered stage map: each stage's kind and gate
.foundry/bin/foundry rubric <stage>    # one stage's rubric, verbatim (the driver's judgment)
```

At each judgment stage, run `.foundry/bin/foundry rubric <stage>` and follow it. Where a
lower-level skill fits a stage, defer to it — it carries the same judgment with its own
fresh-context workflow.

## The walk

Each stage is a **gate**: do not start the next until this one is met.

- [ ] **0 · Frame** — classify the work; pick the entry path (feature runs all; bug-fix and
  refactor enter at build; enhancement enters at spec, light). Supervised: you confirm each
  gate before advancing.
- [ ] **1 · Spec** — the **spec-review** skill (or `rubric spec`): write/refine
  `roadmap/specs/<feature>/{requirements,design,tasks}.md` to `SPEC_REVIEW: CLEAN`. **GATE:
  no code until the design is approved.**
- [ ] **2 · Plan** — `rubric plan`: bite-sized TDD tasks in waves in `tasks.md`; claim the
  card and its worktree (`git worktree add -b card/<id> wt/<id> origin/<default>`). **GATE:
  no code until the plan is approved.**
- [ ] **3 · Build** — `rubric build`: a `features/` Scenario before its code, then TDD
  red→green; stage explicit paths; checkpoint each green step. **GATE: the behavior has its
  Scenario before its code.**
- [ ] **4 · Verify** — run `.foundry/bin/foundry gate`; paste the `gate: PASS` line. **GATE:
  a recorded PASS, not a claim.**
- [ ] **5 · Knowledge** — the **knowledge** skill (or `rubric knowledge`): place the change
  in its home, record provenance, regenerate the index. **GATE: no stale concept or index.**
- [ ] **6 · Review** — the **code-review** skill (or `rubric review`) in fresh context; fix
  every blocking finding yourself, then re-review. **GATE: no unresolved blocking finding
  ships.**
- [ ] **7 · Finish** — commit in your worktree; **ask before you push.** A card is Done when
  its branch merges to the default branch with the gate green — set Done in that PR; retire
  the worktree. **GATE: Done = merged with the gate green.**

## What this skill is not

- **Not deterministic.** No ledger, no code-enforced gate, no retry cap — the supervision is
  yours. When you want the enforced, recorded version, that is `.foundry/bin/foundry run`.
- **Not a copy of the rubrics.** If you are pasting stage judgment here, it belongs in
  `src/foundry/rubrics/<stage>.md`, reached by `.foundry/bin/foundry rubric` — one edit
  updates both the supervised and the headless path.
