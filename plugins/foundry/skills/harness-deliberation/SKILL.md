---
name: harness-deliberation
description: Use when a Foundry spec needs a mediated Codex plus Claude Code design session with recorded prompt, final, decision, snapshot, and spec artifacts.
---

# Harness Deliberation

Run a two-harness mediated design session for a Foundry repo. The broker owns
session storage, preflight, turns, decisions, replay, snapshots, and generated
spec files.

## Runner

Use the wrapper for a new session:

```bash
plugins/foundry/skills/harness-deliberation/scripts/spawn-deliberation.sh \
  --prompt <prompt.md> --session <session-id> [--attach] [repo-root]
```

The wrapper delegates to:

```bash
plugins/foundry/scripts/harness-deliberation-broker.py start \
  --prompt <prompt.md> --session <session-id> --repo <repo-root> [--attach]
```

## V1 Commands

- `start --prompt <file> --session <id> [--attach]`
- `round`
- `decide --file <file.json>`
- `rebuild`
- `spec --out roadmap/specs/<feature>`
- `live-smoke --session <id> [--prompt <file>]`

## Rules

- V1 has exactly two participants: Codex and Claude Code.
- `live-smoke` is opt-in because it spends real harness turns.
- The mediator records questions and decisions.
- Raw CLI output is debug evidence only.
- Generated specs still need downstream `spec-review`.
