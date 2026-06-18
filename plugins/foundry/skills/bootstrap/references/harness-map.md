# Harness map

The per-harness coupling points foundry binds. Everything else is single-source:
`AGENTS.md` (instructions) and `SKILL.md` (Agent Skills standard, `name` +
`description` frontmatter). Adding a harness is a row here, not new machinery.

| Coupling point | Claude Code | Codex |
|---|---|---|
| Instruction file | `CLAUDE.md` → `AGENTS.md` (pointer) | `AGENTS.md` (native) |
| Skill location | `<plugin root>/skills/<name>/` | `.agents/skills/<name>/` |
| Skill invocation | `/foundry:<name>` | `$<name>` |
| Fresh session runner | `spawn-fresh-session.sh` starts `claude` in tmux | `spawn-fresh-session.sh` starts `codex` in tmux |
| Distribution | `.claude-plugin/{marketplace,plugin}.json` | `.agents/plugins/marketplace.json` (neutral) + `.codex-plugin/plugin.json` |
| Plugin-root reference | `${CLAUDE_PLUGIN_ROOT}` | Codex plugin root (tree co-located) |

## Single source

- **Instructions** — one `AGENTS.md`. Claude Code reads a `CLAUDE.md` that points to it;
  every other harness reads `AGENTS.md` natively. Emit `CLAUDE.md` only when Claude Code
  is a selected harness.
- **Skills** — one `SKILL.md` per skill. Bodies name other skills by intent, never a
  harness-specific command form.
- **Templates** — resolved as `<plugin root>/templates/`, the root bound per harness in
  the table; never a layout-relative `../../` path.

## Verified against codex 0.139.0

- Distribution: Codex discovers `foundry@foundry` via a neutral `.agents/plugins/marketplace.json`
  (the `.agents/` family, like `.agents/skills/`) + a Codex-native `plugins/foundry/.codex-plugin/plugin.json`
  — verified with both `.claude-plugin/` dirs removed, so neither harness reads the other's
  manifest. Plugin tree co-located, so `<plugin root>` resolves.
- Fresh session runner: lifecycle skills use `plugins/foundry/scripts/spawn-fresh-session.sh`
  through thin skill wrappers. The runner writes the full prompt to
  `.foundry/tmp/fresh-session/<id>/prompt.md`, then starts the same harness in tmux
  with a short "read this prompt file" instruction. Harness-specific behavior stays
  in the runner's command adapter.
- Sandbox modes: `read-only` / `workspace-write` / `danger-full-access`.
- Open: the manifest key that exposes `agents/` (skills pointer confirmed).

## Adding a harness

A new column: its instruction file (or `AGENTS.md`-native), skill location + invocation,
fresh-session command adapter, distribution manifest, and plugin-root reference. No
skill body or template change.
