> **Status:** Ready (2026-06-16) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md).

# Design — harness-agnostic foundry

## Architecture overview

`foundry-core` already split the system in two: **portable repo files** (`AGENTS.md`,
glossary, board, gates, features) that any tool follows, and **Claude-native plugin
machinery** (skill triggering, the review agent, the interview). This feature
generalizes "Claude-native" to "**harness**-native" and pins the coupling to four
points — everywhere else stays single-source.

Foundry touches a **harness** (the glossary term) in exactly four places:

1. **Instruction file** — what the harness auto-loads as project context.
2. **Skill install + invocation** — where skill files live and how the user calls them.
3. **Subagent format** — how `spec-reviewer` is defined and dispatched.
4. **Distribution manifest** — how a user installs foundry for that harness.

The design is a **harness map**: one table giving these four values per harness. The
two standards do the heavy lifting — `AGENTS.md` for (1) and the Agent Skills
`SKILL.md` format for (2) — so each map entry is small. Adding the harness after
Codex is a new row (AC-4 extensibility), not new machinery.

## The harness map

| Coupling point | Claude Code | Codex | Single source |
|---|---|---|---|
| Instruction file | `CLAUDE.md` → `AGENTS.md` (pointer) | `AGENTS.md` (native) | `AGENTS.md` |
| Skill location | `plugins/foundry/skills/<name>/` (plugin) | `.agents/skills/<name>/` (plugin-distributed) | one `SKILL.md` per skill |
| Skill invocation | `/foundry:<name>` | `$<name>` | referenced by name, not command form |
| Subagent | `agents/spec-reviewer.md` (frontmatter + body) | `agents/spec-reviewer.md` (same `.md` format, plugin-bundled) | one shared `agents/spec-reviewer.md` |
| Distribution | `.claude-plugin/{marketplace,plugin}.json` | `.agents/plugins/marketplace.json` (neutral) + `.codex-plugin/plugin.json` | the plugin's `skills/` + `agents/` tree |
| Plugin-root ref | `${CLAUDE_PLUGIN_ROOT}` | Codex plugin root (tree co-located, verified) | the placeholder `<plugin root>` |

`AGENTS.md` and the `SKILL.md` bodies are written **once**; only the thin per-harness
wrappers (the pointer file, the subagent envelope, the manifest, the invocation
token) vary. This is the no-divergent-content rule from requirements Out-of-scope.

## Components

| Component | Location | New / mod | Purpose |
|---|---|---|---|
| `harness` glossary term | `knowledge/glossary.md` | mod | Canonical vocabulary (AC-1.1) |
| Harness map | `plugins/foundry/skills/*/references/` or a shared skill ref | new | The table above, the source skills read for per-harness behavior (AC-2, AC-3) |
| Plugin-root resolution | `bootstrap`/`update` `SKILL.md` | mod | Replace fragile `<base dir>/../../templates/` with `<plugin root>/templates/`, resolved per harness (AC-2.4) |
| Invocation neutralization | `bootstrap`/`code`/`update` `SKILL.md` | mod | Name skills by intent, not `/foundry:<name>` (AC-2.3) |
| `spec-reviewer` (single shared file) | `agents/spec-reviewer.md` | mod | One `.md` agent both harnesses read; no twin, no drift (AC-2.6) |
| `code` dispatch rule | `code` `SKILL.md` §1 | mod | Delegate review via the harness's subagent mechanism, inline fallback (AC-2.5) |
| Codex distribution | `plugins/foundry/.codex-plugin/plugin.json` + Codex marketplace entry (+ install doc) | new | A Codex user installs foundry whole (AC-2.7) |
| Harness interview question | `bootstrap` `SKILL.md` §2 | mod | Select target harness(es) (AC-3.1) |
| Conditional instruction pointer | `bootstrap` `SKILL.md` §4, `generate.md` | mod | `CLAUDE.md` iff Claude selected (AC-3.2) |
| Rules relocation | `templates/seeds/.claude/rules/` → `templates/seeds/rules/` | mod | Harness-neutral convention path (AC-3.3, AC-4.2) |
| Manifest: `harnesses` field + move to `.foundry/manifest.json` | `bootstrap` §3, `update` §1, manifest schema | mod | Record the selected set; relocate into the `.foundry/` state dir (AC-3.4, AC-4.7) |
| convention-3 migration | `update/references/migrations/{README.md,harness-agnostic.md}` | new | Retrofit convention-2 repos (AC-4) |
| `knowledge.py` skill path | `templates/verbatim/scripts/knowledge.py` | mod (small) | Existence-guarded check learns `.agents/skills/` too |
| Codex eval engine + fixtures | `evals/harness/`, `evals/fixtures/` | new | Independent verification (AC-5) |

## Data models

**Manifest, at `.foundry/manifest.json`** (beside `conventionVersion`):

```json
{ "pluginVersion": "1.1.0", "conventionVersion": 3,
  "harnesses": ["claude-code", "codex"], "files": { … } }
```

Absent `harnesses` → a repo bootstrapped before this feature; the convention-3
migration infers `["claude-code"]` (the only harness foundry served then) and stamps
it. `update` reads `harnesses` as the source of truth and does **not** re-interview;
only an explicit add/remove changes the set (AC-4.4, AC-4.6). The manifest lives in a
`.foundry/` repo-state directory the convention-3 migration creates, moving it from
the legacy top-level `.foundry-manifest.json` (AC-4.7); `update` reads
`.foundry/manifest.json` first, the legacy path as fallback. The directory holds the
manifest only — the rest of the interview lives single-source in the files it
generated (`AGENTS.md`, glossary, board), so re-storing it would invite drift.

**`spec-reviewer` — one shared file.** Verified against `codex` 0.139.0: Codex reads
plugin agents as `agents/*.md` (markdown + frontmatter), the same format Claude Code
uses. Foundry's existing `agents/spec-reviewer.md` serves both harnesses unchanged — no
Codex twin, no drift guard. Read-only holds via its `tools: Read, Grep, Glob`
frontmatter (and `--sandbox read-only` when run as a Codex subagent).

**Codex distribution — harness-appropriate, never `.claude-plugin/`.** Verified live:
Codex discovers `foundry@foundry` via a neutral `.agents/plugins/marketplace.json` (the
`.agents/` family, like `.agents/skills/`) + a Codex-native
`plugins/foundry/.codex-plugin/plugin.json` (with an `interface` block) — confirmed with
both `.claude-plugin/` directories removed. Claude Code reads `.claude-plugin/`; neither
harness reads the other's manifest. The skills + `spec-reviewer.md` stay shared.

## Plugin-root resolution

Today the skills name templates as `<base dir>/../../templates/` — a path that only
resolves in the Claude plugin's nested layout (`skills/<name>/` and `templates/` as
siblings two levels up). Codex distributes skills into `.agents/skills/`; the
sibling `templates/` need not survive, so `../../` is fragile.

**Fix:** replace `<base dir>/../../templates/` with **`<plugin root>/templates/`**,
where `<plugin root>` is the harness's own plugin-root reference (Claude
`${CLAUDE_PLUGIN_ROOT}`; the Codex equivalent). Each harness resolves a stable root;
templates ride along in the plugin tree, co-located under both harnesses (verified: the `superpowers` Codex plugin ships `skills/` beside its plugin root).
The skill body carries the neutral placeholder; the harness map binds it. This
satisfies AC-2.4 and removes a latent bug that also bites any non-default Claude
install layout.

## Data flow

**Bootstrap (multi-harness).** Inspect → **Interview** now asks the harness set
(AC-3.1) → **Copy** places rules at `rules/` (AC-3.3) → **Generate** writes `AGENTS.md`
once, then a `CLAUDE.md` pointer only if Claude is selected (AC-3.2), and stamps
`harnesses` + `conventionVersion: 3` (AC-3.4) → **Verify** asserts each selected
harness's instruction file resolves and no unselected-harness shim exists (AC-3.5).

**Foundry under Codex (Axis A).** User installs the Codex plugin (AC-2.7) → invokes
`$bootstrap` (AC-2.1) → the skill resolves templates via `<plugin root>/templates/`
(AC-2.4) → on the `code` lifecycle, review is delegated to the Codex `spec-reviewer`
subagent, or run inline if absent (AC-2.5) → the interview, finding no question tool,
takes canned answers (AC-3.1, already in `bootstrap` §2).

**Retrofit (convention 3).** `/foundry:update` reads the manifest; `conventionVersion
< 3` (or absent) selects the harness-agnostic migration (AC-4.1). Under the
`migration-aware-update` safety frame (clean tree → dry-run → branch → no-regression,
AC-4.5): `git mv` the rules off `.claude/` and the manifest into `.foundry/`, rewrite
references (AC-4.2, AC-4.7), infer and stamp `harnesses` + `conventionVersion: 3`
(AC-4.3). The detector keys on the legacy top-level manifest and `.claude/rules/`,
both of which the migration removes — so a convention-3 repo's detector does not fire
(AC-4.5).

**Add a harness.** `/foundry:update`, asked to add harness `<harness>`, emits only
that harness's pointer — a `CLAUDE.md` for Claude, nothing for a native-`AGENTS.md`
harness — and adds it to the manifest set, idempotently (AC-4.4).

## Error handling

| Failure mode | Handling |
|---|---|
| Harness offers no question tool (Codex) | Interview takes canned answers; never blocks (AC-3.1) |
| Harness has no subagent mechanism | `code` runs the review inline against the same criteria; never skips (AC-2.5) |
| `<plugin root>` unresolved | Skill stops with a clear "templates not found under <root>" — never silently proceeds with a wrong path |
| Codex `exec` read-only default during a bootstrap eval | Harness runs `codex exec --sandbox workspace-write --skip-git-repo-check`; a read-only run that writes nothing is a harness misconfig, reported |
| Unselected-harness shim present after bootstrap | AC-3.5 verification fails the bootstrap |
| Migration on a dirty tree / unplaceable convention | Inherited from `migration-aware-update`: refuse / stop-and-ask, no guess |

## Testing strategy

**Independent oracle (AC-5.1).** Grading stays harness-owned — fixtures plus scans
that share no code with foundry's skills; a skill never grades itself. Extends the
existing Layer-1/2/3 model.

| Eval | Pattern | Asserts |
|---|---|---|
| Codex bootstrap e2e (AC-5.2) | `codex exec --sandbox workspace-write --skip-git-repo-check` over each stack fixture, mirroring `claude -p --plugin-dir` | bootstrap green end-to-end under Codex; gate discrimination holds |
| Multi-harness readability (AC-5.3) | bootstrap a fixture for `[claude-code, codex]`; harness-owned file scan | `AGENTS.md` present; `CLAUDE.md` present iff Claude selected; rules at `rules/`, none under `.claude/`; manifest `harnesses` correct |
| Convention-3 migration (AC-5.4) | the `migration-eval` frame on a convention-2 fixture | rules relocated, references rewritten, `harnesses` stamped, `conventionVersion 3`, idempotent re-run, gate no-regression; a **seeded incomplete migration** (a stray `.claude/rules/` ref) the harness scan must fail |
| `spec-reviewer` parity (AC-5.5) | run the shared criteria under both harness wrappers against the `reviewer` fixture | same findings, same decoys avoided, across Claude Code and Codex |

**Fixture matrix.** Reuse `rust-cli`, `python-service`, `ts-monorepo` for the Codex
bootstrap eval (cross-stack), the `reviewer` fixture for parity, and a convention-2
snapshot (frozen by the existing fixture-builder) for the migration. Each carries a
discrimination variant the harness scan must fail.

**No drift guard needed (AC-2.6).** `spec-reviewer` is a single `agents/spec-reviewer.md`
both harnesses read — no second wrapper to sync. The parity eval above still confirms the
one file behaves the same under each harness.

## Performance

Negligible at runtime — bootstrap and migration are one-time human-initiated acts.
CI cost rises: the Codex bootstrap eval adds a second engine to Layer 2. Gate it to
PRs touching skills, templates, or the harness map, as Layer 2 already scopes.

## Migration / backward-compatibility

- **Pre-feature repos** carry no `harnesses` and `conventionVersion ≤ 2`; the
  convention-3 migration places them (`["claude-code"]`) and stamps both fields. The
  common path.
- **Bootstrap starts stamping** `harnesses` + `conventionVersion: 3` going forward.
- **Two structural moves earn convention 3** — `.claude/rules/` → `rules/` and
  `.foundry-manifest.json` → `.foundry/manifest.json` (the glossary's "moves
  directories" trigger); the `harnesses` field is additive. `update` reads the new
  manifest path, legacy as fallback.
- **No downgrade.** Recovery is `git revert`, per `migration-aware-update`.
- **Claude-only repos keep their behavior** — `CLAUDE.md` still points at `AGENTS.md`;
  the migration moves the rules and the manifest and rewrites references, nothing more.

## Self-hosting

This feature changes the conventions foundry itself runs on — a self-referential
migration. Foundry solves it the way compilers do, with a **staged bootstrap**; three
rules keep it sound.

**Build the new with the old.** Waves 1–5 are authored and validated under the current
working harness (Claude Code); foundry adopts the new layout for its own development
only after the Codex path is green there. The new toolchain is built by the old before
it builds itself (GCC stage 1 → stage 2) — never migrate the self-host ahead of the
working path.

**Converge to a fixpoint.** Foundry's own setup must equal what its bootstrap emits for
its declared harnesses (`[claude-code, codex]`): rules at `rules/`, manifest at
`.foundry/manifest.json`, `AGENTS.md` + a `CLAUDE.md` pointer. The byte-identity gate
already enforces this for verbatim templates; the readability scan (T17) runs against
foundry's *own* repo as a fixture — foundry is its own fixture, the stage-3
"rebuild equals stage 2" gate.

**Dogfood under Codex.** The credible proof that foundry runs under Codex is foundry
running under Codex on itself: a `codex exec` invocation of a foundry skill in foundry's
own repo, gated like any merge. The tool that makes repos harness-agnostic is
itself developed harness-agnostically — precedent exists (`wshobson/agents` ships a
single Markdown source consumed natively by Claude Code, Codex, Cursor, and more).

## Open questions to confirm at build

Resolved at Wave 2 against `codex` 0.139.0: the plugin manifest
(`.codex-plugin/plugin.json`, mirrors the Claude one), the subagent format (`agents/*.md`,
shared with Claude Code), the sandbox modes, and the co-located plugin tree (so
`<plugin root>/templates/` resolves). Remaining:

1. The `.codex-plugin/plugin.json` key that exposes `agents/` (the `skills` pointer is
   confirmed).
2. Whether any current consumer auto-loads `.claude/rules/` via a `CLAUDE.md` import
   (vs. reference-by-path) — if so, the migration rewrites that import too.

## Acceptance-criteria traceability

| AC | Design coverage |
|---|---|
| 1.1 harness term | Components (glossary); Architecture |
| 1.2 manifest term update | Data models; §Migration |
| 2.1 skills under Codex | Harness map; Data flow (Axis A) |
| 2.2 frontmatter minimal | Harness map (single-source `SKILL.md`); check-fast frontmatter guard |
| 2.3 no hardcoded invocation | Components (invocation neutralization) |
| 2.4 template resolution | §Plugin-root resolution |
| 2.5 dispatch or inline | Components (`code` dispatch); Error handling |
| 2.6 shared `spec-reviewer` | Data models (single file); Testing (parity eval) |
| 2.7 Codex install path | Data models (`plugin.json`); harness map |
| 3.1 interview asks | Data flow (Bootstrap); Error handling |
| 3.2 AGENTS.md + conditional CLAUDE.md | Data flow; harness map |
| 3.3 neutral rules path | Components (rules relocation) |
| 3.4 manifest harness set | Data models (manifest) |
| 3.5 per-harness readability | Data flow (Verify); Testing (readability eval) |
| 4.1 registry entry | Components; Data flow (Retrofit) |
| 4.2 move rules, keep history | Data flow (Retrofit); Migration |
| 4.3 stamp harnesses + v3 | Data models; Migration |
| 4.4 add-a-harness | Data flow (Add a harness) |
| 4.5 safety + idempotent | Data flow (Retrofit); inherited from `migration-aware-update` |
| 4.6 no re-prompt | Data models (manifest note); Data flow |
| 4.7 manifest relocation | Data models; Data flow (Retrofit); §Migration |
| 5.1 independent oracle | Testing (independence) |
| 5.2 Codex e2e | Testing (Codex bootstrap eval) |
| 5.3 readability | Testing (readability eval) |
| 5.4 migration | Testing (migration eval) |
| 5.5 reviewer parity | Testing (parity eval) |
| 5.6 self-host converge + dogfood | §Self-hosting; Testing |
