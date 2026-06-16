> **Status:** Ready (2026-06-16) — tracked on the [board](../../ROADMAP.md).

# Tasks — harness-agnostic foundry

Waves run top to bottom; tasks within a wave have no inter-dependencies. Build order
follows the design's three axes after a shared foundation: vocabulary + the harness
map first (everything reads them), then Axis A (foundry under Codex), Axis B (bootstrap
emission), Axis C (the retrofit migration), then the independent-oracle evals. Breadth
beyond Claude Code + Codex accretes COE-style (Deferred). Per the design's staged
bootstrap, Waves 1–5 build and validate under Claude Code; foundry adopts the new
conventions for its own development last (Wave 6), once the Codex path is green.

## Wave 1: Foundation — vocabulary + harness map (no dependencies)

- [ ] **T1** Glossary: add **harness** (prior art *agent-harness engineering*; debt
  terms *agent*-as-tool and *host*; *agent* and *subagent* preserved); update the
  **Manifest** and **Convention version** entries to `.foundry/manifest.json` and note
  the `harnesses` field — `knowledge/glossary.md`. → AC-1.1, AC-1.2
- [ ] **T2** Harness map: the per-harness table (instruction file · skill location +
  invocation · subagent format · distribution manifest · plugin-root reference) that
  bootstrap, update, and code read for per-harness behavior; seed it with Claude Code
  and Codex — `plugins/foundry/skills/bootstrap/references/harness-map.md`.
  → AC-2 / AC-3 foundation

## Wave 2: Foundry under Codex — Axis A (depends: Wave 1)

- [ ] **T3** Plugin-root resolution: replace `<base dir>/../../templates/` with
  `<plugin root>/templates/`, bound per harness by the map; stop on an unresolved root
  — `plugins/foundry/skills/{bootstrap,update}/SKILL.md`. → AC-2.4
- [ ] **T4** Invocation neutralization: reference skills by name/intent, not the
  `/foundry:<name>` command form; keep each `SKILL.md` frontmatter to `name` +
  `description` — `plugins/foundry/skills/{bootstrap,code,update}/SKILL.md`.
  → AC-2.2, AC-2.3
- [ ] **T5** `spec-reviewer`, shared single file: confirm `agents/spec-reviewer.md`
  frontmatter is Codex-clean (the subset both harnesses honor) so the one `.md` serves
  both; read-only holds via its `tools` frontmatter. No twin, no drift guard (verified:
  Codex reads `agents/*.md`) — `plugins/foundry/agents/spec-reviewer.md`.
  → AC-2.6, AC-2.5 (definition)
- [ ] **T6** `code` dispatch rule: delegate review through the running harness's
  subagent mechanism, inline fallback where none exists — never skip —
  `plugins/foundry/skills/code/SKILL.md`. → AC-2.5
- [x] **T7** Codex distribution: none needed — verified live that Codex reads foundry's
  existing `.claude-plugin/` marketplace + plugin manifests directly (`codex plugin
  marketplace add` discovers `foundry@foundry`). Document the Codex install path —
  `knowledge/releasing.md`. → AC-2.7, AC-2.1

## Wave 3: Bootstrap emission — Axis B (depends: Waves 1–2)

- [ ] **T8** Interview harness question (§2): ask the target harness(es) — Claude Code,
  Codex, multi-select — with a canned-answer fallback where the harness has no question
  tool — `plugins/foundry/skills/bootstrap/SKILL.md`. → AC-3.1
- [ ] **T9** Generate (§4): `AGENTS.md` single-source; emit the `CLAUDE.md` pointer
  only when Claude Code is selected; emit no shim for an unselected harness —
  `plugins/foundry/skills/bootstrap/SKILL.md`, `…/references/generate.md`. → AC-3.2
- [ ] **T10** Rules relocation: move the seed `templates/seeds/.claude/rules/` →
  `templates/seeds/rules/`; rewrite every reference (generate, verify, `code`,
  `knowledge-config.json`); move foundry's own `.claude/rules/` → `rules/` for
  self-host consistency — `plugins/foundry/templates/seeds/rules/`, `.claude/rules/` →
  `rules/`, references. → AC-3.3
- [ ] **T11** Manifest at `.foundry/manifest.json`: add the `harnesses` field; bootstrap
  writes the manifest there and stamps `conventionVersion: 3` —
  `plugins/foundry/skills/bootstrap/SKILL.md` (§3). → AC-3.4
- [ ] **T12** `knowledge.py` harness-aware: the existence-guarded skill-ref check learns
  `.agents/skills/` alongside `.claude/skills/`; `skill_ref_prefixes` learns the new
  `rules/` path — `plugins/foundry/templates/verbatim/scripts/knowledge.py`,
  `…/templates/seeds/knowledge/knowledge-config.json`. → AC-3.3
- [ ] **T13** Verify per-harness readability (§5): assert each selected harness's
  instruction file resolves and no unselected-harness shim exists —
  `plugins/foundry/skills/bootstrap/SKILL.md`, `…/references/verify.md`. → AC-3.5

## Wave 4: Retrofit migration — Axis C (depends: Wave 3)

- [ ] **T14** Convention-3 registry entry + `harness-agnostic` playbook: detect (legacy
  top-level `.foundry-manifest.json` OR `.claude/rules/`); dry-run plan; `git mv` rules
  → `rules/` and manifest → `.foundry/manifest.json`; rewrite references; infer + stamp
  `harnesses` + `conventionVersion 3`; idempotent detector; safety frame inherited from
  `migration-aware-update` — `plugins/foundry/skills/update/references/migrations/{README.md,harness-agnostic.md}`.
  → AC-4.1, AC-4.2, AC-4.3, AC-4.5, AC-4.7
- [ ] **T15** Update read-path + add-a-harness (§1): read `.foundry/manifest.json` with
  a legacy-top-level fallback; maintain the recorded harness set without re-asking;
  add/remove a harness emits only that harness's shim and updates the set —
  `plugins/foundry/skills/update/SKILL.md`. → AC-4.4, AC-4.6, AC-4.7 (read-fallback)

## Wave 5: Evals — independent oracle (depends: the features they test)

- [ ] **T16** Codex bootstrap e2e: `codex exec --sandbox workspace-write
  --skip-git-repo-check` over a stack fixture; harness-owned invariants + gate
  discrimination; confirm the `codex exec` flags against a live `codex` —
  `evals/harness/codex-bootstrap-eval.sh`. → AC-5.2 (independent oracle, AC-5.1)
- [ ] **T17** Multi-harness readability: bootstrap a fixture for `[claude-code, codex]`;
  a harness-owned scan asserts `AGENTS.md` present, `CLAUDE.md` iff Claude, rules at
  `rules/`, manifest at `.foundry/manifest.json` with the right `harnesses`, and no
  `.claude/` shim — `evals/harness/harness-readability-eval.sh`. → AC-5.3
- [ ] **T18** Convention-3 migration: a frozen convention-2 fixture; run update; a
  harness-owned scan asserts rules + manifest relocated, references rewritten,
  `harnesses` stamped, `conventionVersion 3`, idempotent re-run, gate no-regression;
  a **seeded incomplete migration** (a stray top-level manifest or `.claude/rules/`
  ref) the scan must fail — `evals/harness/harness-migration-eval.sh`,
  `evals/fixtures/harness-migration-*/`. → AC-5.4
- [ ] **T19** `spec-reviewer` parity: run the shared criteria under both wrappers
  against the `reviewer` fixture; compare findings — `evals/harness/reviewer-parity-eval.sh`.
  → AC-5.5
- [ ] **T20** Self-host convergence + dogfood: run the T17 readability scan against
  foundry's own repo (foundry is its own fixture); run a foundry skill under `codex
  exec` in foundry's repo — staged after T16 is green under Claude Code —
  `evals/harness/selfhost-eval.sh`. → AC-5.6

## Wave 6: Verification

- [ ] Run `scripts/check-fast.sh` — foundry self-host gate (plugin validate,
  byte-identity, knowledge check, script tests). Must PASS.
- [ ] Confirm T16–T19 evals green; paste results.
- [ ] Regression: the existing `claude -p` bootstrap / update / migration evals stay
  green — the changes are structural and additive.
- [ ] Self-host: foundry's own `.claude/rules/` → `rules/` move applied; foundry
  declares `harnesses = [claude-code, codex]`; passes the T20 convergence + dogfood
  evals; its glossary names the new manifest path.
- [ ] Manually verify each acceptance criterion against the implementation.
- [ ] Board: set the Epic-4 `roadmap/ROADMAP.md` cards to Validating with the recorded
  gate + eval results.
- [ ] Capture deferred breadth as `roadmap/BACKLOG.md` items.

## Deferred — breadth (accrete COE-style)

The harness map makes a third harness a row, not a rewrite; the eval safety net makes an
un-covered case fail loudly, not catastrophically — so breadth accretes as need surfaces:

- Harnesses beyond Claude Code + Codex (Gemini CLI, Cursor, …) — a map row + a
  readability/run eval each.
- Plugin-root **bundling fallback** if Codex flattens skills out of the plugin layout
  (design open question 2) — bundle templates per-skill instead of a shared root.
- Migration breadth fixtures — customized rules, scale (dozens of concepts), partial
  hand-migration — beyond the tier-1 happy path.

## Acceptance-criteria traceability

| AC | Built by | Tested by |
|---|---|---|
| 1.1 harness term | T1 | knowledge check; T19 (reviewer self-check) |
| 1.2 manifest/convention-version entries | T1 | knowledge check |
| 2.1 skills under Codex | T3, T4, T7 | T16 |
| 2.2 frontmatter minimal | T4 | check-fast guard |
| 2.3 no hardcoded invocation | T4 | T16 |
| 2.4 template resolution | T3 | T16 |
| 2.5 dispatch or inline | T5, T6 | T16, T19 |
| 2.6 shared spec-reviewer | T5 | T19 (parity) |
| 2.7 Codex install path | T7 | T16 (install + run) |
| 3.1 interview asks | T8 | T17 |
| 3.2 AGENTS.md + conditional CLAUDE.md | T9 | T17 |
| 3.3 neutral rules path | T10, T12 | T17 |
| 3.4 manifest harness set + `.foundry/` | T11 | T17 |
| 3.5 per-harness readability | T13 | T17 |
| 4.1 registry entry | T14 | T18 |
| 4.2 move rules | T14 | T18 |
| 4.3 stamp harnesses + v3 | T14 | T18 |
| 4.4 add-a-harness | T15 | T18 |
| 4.5 safety + idempotent | T14, T15 | T18 (inherited from migration-aware-update) |
| 4.6 no re-prompt | T15 | T18 |
| 4.7 manifest relocation | T14, T15 | T18 |
| 5.1 independent oracle | T16–T19 graders | property of each eval |
| 5.2 Codex e2e | T16 | Wave 6 |
| 5.3 readability | T17 | Wave 6 |
| 5.4 migration | T18 | Wave 6 |
| 5.5 reviewer parity | T19 | Wave 6 |
| 5.6 self-host converge + dogfood | T20 | Wave 6 |
