---
name: handoff
description: Use when a milestone is done and a fresh agent should continue the same work with durable state, verified context, and the same agent harness.
---

# Handoff

Write a concise handoff briefing, store it in repo-local generic agent state,
then spawn a successor with the same harness.

## Workflow

1. Gather ground truth with commands:
   - branch: `git branch --show-current`
   - HEAD: `git rev-parse --short HEAD`
   - recent commits: `git log --oneline -8`
   - working tree: `git status --short`
   - change size: `git diff --stat` and `git diff --cached --stat`
2. Read existing handoff state:
   - preferred: `.agent/handoff/HANDOFF.md`
   - legacy fallback: `.claude/handoff/HANDOFF.md`
3. Write `.agent/handoff/HANDOFF.md`. Create the directory if needed.
4. Print the full briefing so the user can see the exact state.
5. Spawn the successor with `scripts/spawn-successor.sh "<slug>"`.

## Briefing Shape

Use these sections:

1. **Mission**: standing goal and source of truth.
2. **State (verified)**: HEAD, committed state, uncommitted caveat, last gate result.
3. **What happened and why**: decisions, rationale, dead ends, gotchas.
4. **Next unit of work**: one ordered action that fits in a single pass.
5. **Open decisions**: unresolved choices with options. Omit when empty.
6. **Guardrails**: gates, conventions, and what not to touch.
7. **Done when**: commands and expected output that prove completion.

Prefer paths, commands, hashes, metrics, and file anchors over transcript summary.

## Spawn

Derive a short lowercase slug from the next unit of work, then run:

```bash
scripts/spawn-successor.sh "<slug>"
```

The script detects `claude`, `codex`, or `pi` and opens a tmux window or detached
tmux session with that same harness. If tmux or harness detection is unavailable,
it prints the manual command and seed prompt.

## Common Mistakes

- Do not dump the transcript. Compress it into decisions, evidence, and next action.
- Do not invent gate results. Say what was not run.
- Do not write only `.claude/handoff/HANDOFF.md`; new handoffs use `.agent/handoff/HANDOFF.md`.
- Do not spawn before the briefing is written and printed.
