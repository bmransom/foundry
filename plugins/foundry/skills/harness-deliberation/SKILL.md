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

## Live view (optional)

From inside a tmux pane (e.g. an active Claude Code session), run the round with two
ephemeral viewer panes — codex | claude — opened ABOVE your pane and closed when the
round finishes; mediate from the chat afterward:

```bash
plugins/foundry/skills/harness-deliberation/scripts/round-inline.sh --session-dir <dir>
```

## V1 Commands

- `start --prompt <file> --session <id> [--attach]`
- `round`
- `decide --file <file.json>`
- `rebuild`
- `spec --out roadmap/specs/<feature>`
- `live-smoke --session <id> [--prompt <file>]`
- `pane-command --session-dir <dir> --actor codex|claude-code` (viewer-pane tail of that turn's latest final.md)

## Rules

- V1 has exactly two participants: Codex and Claude Code.
- `live-smoke` is opt-in because it spends real harness turns.
- The mediator records questions and decisions.
- Raw CLI output is debug evidence only.
- Generated specs still need downstream `spec-review`.
