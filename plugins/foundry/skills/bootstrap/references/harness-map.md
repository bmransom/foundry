# Harness map

The per-harness coupling points foundry binds. Everything else is single-source:
`AGENTS.md` (instructions) and `SKILL.md` (Agent Skills standard, `name` +
`description` frontmatter). Adding a harness is a row here, not new machinery.

| Coupling point | Claude Code | Codex |
|---|---|---|
| Instruction file | `CLAUDE.md` → `AGENTS.md` (pointer) | `AGENTS.md` (native) |
| Skill location | `<plugin root>/skills/<name>/` | `.agents/skills/<name>/` |
| Skill invocation | `/foundry:<name>` | `$<name>` |
| Subagent | `agents/<name>.md` (YAML frontmatter + body) | `.codex/agents/<name>.toml` (`developer_instructions`, `sandbox_mode`) |
| Distribution | `.claude-plugin/{marketplace,plugin}.json` | `plugin.json` (`components`) |
| Plugin-root reference | `${CLAUDE_PLUGIN_ROOT}` | Codex plugin root (verify) |

## Single source

- **Instructions** — one `AGENTS.md`. Claude Code reads a `CLAUDE.md` that points to it;
  every other harness reads `AGENTS.md` natively. Emit `CLAUDE.md` only when Claude Code
  is a selected harness.
- **Skills** — one `SKILL.md` per skill. Bodies name other skills by intent, never a
  harness-specific command form.
- **Templates** — resolved as `<plugin root>/templates/`, the root bound per harness in
  the table; never a layout-relative `../../` path.

## Verify against a live harness (build-time)

- Codex plugin-root reference, and whether the plugin layout survives install — else
  bundle templates per-skill.
- Codex `plugin.json` `components` schema — `/codex/plugins/build`.
- Codex subagent `.toml` fields and the read-only sandbox — `/codex/config-reference`.

## Adding a harness

A new column: its instruction file (or `AGENTS.md`-native), skill location + invocation,
subagent format, distribution manifest, and plugin-root reference. No skill body or
template change.
