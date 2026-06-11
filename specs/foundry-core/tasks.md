# Foundry core — tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Waves 1–2 done (2026-06-10); Waves 3–7 scope-locked, each planned at claim time per the lifecycle Plan stage — tracked on the [board](../../docs/ROADMAP.md). Wave 1 code blocks below were synced with the post-review fixes (marketplace validate in the gate, EMPTY-TEMPLATE check, no-tests guard, install-hooks hook-count guard) so the plan remains a faithful account of what shipped.

**Goal:** Ship foundry v1 — an installable Claude Code plugin whose bootstrap installs the octant-style setup into any repo, with evals that grade changes.

**Architecture:** A marketplace repo containing one plugin (skills + agent + verbatim templates), self-hosted: foundry develops under its own conventions, and a byte-identity gate keeps its own copies of verbatim templates in sync with `plugins/foundry/templates/`. The template tree mirrors consumer-repo layout (`templates/scripts/docs.py` installs to `scripts/docs.py`).

**Tech Stack:** Bash (gates, hooks), Python 3 (docs.py), Claude Code plugin manifests (JSON), vitepress (docs), GitHub Actions (CI backstop).

## Wave map (spec coverage)

| Wave | Scope | Spec coverage | Detail |
|---|---|---|---|
| 1 | Plugin skeleton + self-host gate + CI | design §Shape, AC-5.1 (gate + byte-identity), AC-2.3 (version field) | below |
| 2 | Template extraction from octant: `docs.py` (config block; new `outline` + `section` subcommands per design §Tooling decisions) + `test_docs.py`, `board.sh`, vitepress scaffold, `ROADMAP`/`BACKLOG`/`glossary`/`validation`/`index`/`specs-README`/`features-README`/`spec-conventions`/COE templates, `worktree-retire.sh`; foundry adopts each as it lands | AC-1.1, AC-1.6, AC-6.1, design §Split | at claim |
| 3 | `code` lifecycle skill + `spec-reviewer` agent, generalized (commands/paths/entity model read from consumer repo files); prior-art naming step in the Spec stage; context-budget lint added to `check-fast.sh` once skill/agent prose exists | US-3 (incl. AC-3.4), US-4 (incl. AC-4.3) | at claim |
| 4 | `bootstrap` skill: inspect → interview → copy → generate → verify | US-1 (all ACs), design §Bootstrap flow, §Isolation | at claim |
| 5 | `update` skill: version-marker diff + refresh, flag customized files | AC-2.1, AC-2.2 | at claim |
| 6 | Evals L1–L2: fixtures (rust-cli, python-service, ts-monorepo) with seeded-defect branches, headless harness, gate-discrimination grading | AC-5.2, AC-5.4, AC-6.3 | at claim |
| 7 | Evals L3 + v1.0.0: spec-reviewer precision/recall vs answer keys (seeded violations incl. uncited coined terms and wordy context-resident prose), lifecycle artifact checks, version-bump rule | AC-5.3, AC-2.3 | at claim |

Octant retrofit is outside this spec (board card, spec to write).

---

## Wave 1 — Plugin skeleton + self-host gate

### Task 1: Plugin and marketplace manifests

**Files:**
- Create: `plugins/foundry/.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

- [x] **Step 1: Write the plugin manifest**

```json
{
  "name": "foundry",
  "description": "Bootstrap an AI-assisted engineering setup into any repo: specs, gherkin features, vitepress docs, kanban board, glossary contract, gates, COE-driven evals.",
  "version": "0.1.0",
  "author": { "name": "Brandon Ransom" }
}
```

- [x] **Step 2: Write the marketplace manifest**

```json
{
  "name": "foundry",
  "owner": { "name": "Brandon Ransom" },
  "plugins": [
    {
      "name": "foundry",
      "source": "./plugins/foundry",
      "description": "Bootstrap an AI-assisted engineering setup into any repo."
    }
  ]
}
```

- [x] **Step 3: Validate both**

Run: `claude plugin validate plugins/foundry && claude plugin validate .`
Expected: both report valid. If the marketplace form of the command differs in the installed CLI version, check `claude plugin validate --help` and use the documented invocation; record the working invocation in this file.

- [x] **Step 4: Commit**

```bash
git add plugins/foundry/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "feat(plugin): add plugin and marketplace manifests"
```

### Task 2: Byte-identity check (the self-host gate)

**Files:**
- Create: `scripts/check-byte-identity.sh`
- Test: `tests/byte_identity_test.sh`

- [x] **Step 1: Write the failing test**

```bash
#!/usr/bin/env bash
# Tests for scripts/check-byte-identity.sh against a fixture tree.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../scripts/check-byte-identity.sh"
FIXTURE_ROOT="$(mktemp -d)"
trap 'rm -rf "$FIXTURE_ROOT"' EXIT

make_fixture() {
  fixture="$(mktemp -d "$FIXTURE_ROOT/case.XXXXXX")"
  mkdir -p "$fixture/plugins/foundry/templates/scripts" "$fixture/scripts"
  printf '# foundry-template: tool v1\necho hello\n' > "$fixture/plugins/foundry/templates/scripts/tool.sh"
  printf '# foundry-template: tool v1\necho hello\n' > "$fixture/scripts/tool.sh"
}

fail() { echo "FAIL: $1"; exit 1; }

make_fixture
"$SCRIPT" "$fixture" >/dev/null || fail "identical copy should pass"

make_fixture
printf 'echo hello\n' > "$fixture/scripts/tool.sh"   # marker line absent locally
"$SCRIPT" "$fixture" >/dev/null || fail "marker-only difference should pass"

make_fixture
printf '# foundry-template: tool v1\necho changed\n' > "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "drifted copy should fail"; fi

make_fixture
rm "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "missing copy should fail"; fi

make_fixture
printf '# foundry-template: tool v1\n' > "$fixture/plugins/foundry/templates/scripts/tool.sh"
: > "$fixture/scripts/tool.sh"
if "$SCRIPT" "$fixture" >/dev/null 2>&1; then fail "marker-only template should fail"; fi

echo "byte_identity_test: PASS"
```

- [x] **Step 2: Run it to verify it fails**

Run: `bash tests/byte_identity_test.sh`
Expected: FAIL — `check-byte-identity.sh` does not exist.

- [x] **Step 3: Implement the check**

```bash
#!/usr/bin/env bash
# Self-host gate: foundry's own copies of verbatim templates must be
# byte-identical to plugins/foundry/templates/ (modulo the version-marker line).
# Usage: check-byte-identity.sh [repo-root]   (defaults to this repo)
set -euo pipefail
REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
TEMPLATES="$REPO/plugins/foundry/templates"
[ -d "$TEMPLATES" ] || { echo "byte-identity: PASS (no templates yet)"; exit 0; }

has_violation=0
while IFS= read -r -d '' template_file; do
  relative_path="${template_file#"$TEMPLATES/"}"
  repo_copy="$REPO/$relative_path"
  if ! grep -qvF 'foundry-template:' "$template_file"; then
    echo "byte-identity: EMPTY-TEMPLATE $relative_path (no content besides the marker)"
    has_violation=1
    continue
  fi
  if [ ! -f "$repo_copy" ]; then
    echo "byte-identity: MISSING $relative_path"
    has_violation=1
    continue
  fi
  if ! diff -q <(grep -vF 'foundry-template:' "$template_file") \
               <(grep -vF 'foundry-template:' "$repo_copy") >/dev/null; then
    echo "byte-identity: DRIFT $relative_path"
    has_violation=1
  fi
done < <(find "$TEMPLATES" -type f -print0)

[ "$has_violation" -eq 0 ] && echo "byte-identity: PASS"
exit "$has_violation"
```

- [x] **Step 4: Run the test to verify it passes**

Run: `chmod +x scripts/check-byte-identity.sh tests/byte_identity_test.sh && bash tests/byte_identity_test.sh`
Expected: `byte_identity_test: PASS`

- [x] **Step 5: Commit**

```bash
git add scripts/check-byte-identity.sh tests/byte_identity_test.sh
git commit -m "feat(gate): add byte-identity self-host check with tests"
```

### Task 3: The quick gate (`check-fast.sh`)

**Files:**
- Create: `scripts/check-fast.sh`

This is foundry's own per-repo gate (generated-class, not a template — consumer repos get theirs from the bootstrap skill).

- [x] **Step 1: Write the gate**

```bash
#!/usr/bin/env bash
# The quick gate: lock-free; runs from .githooks/pre-push and CI.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== plugin validate"
claude plugin validate "$REPO/plugins/foundry"
claude plugin validate "$REPO"

echo "== byte identity"
"$REPO/scripts/check-byte-identity.sh"

echo "== script tests"
test_files=("$REPO"/tests/*_test.sh)
[ -e "${test_files[0]}" ] || { echo "check-fast: no test files found in tests/" >&2; exit 1; }
for test_file in "${test_files[@]}"; do
  bash "$test_file"
done

echo "check-fast: PASS"
```

- [x] **Step 2: Run it end to end**

Run: `chmod +x scripts/check-fast.sh && scripts/check-fast.sh`
Expected: final line `check-fast: PASS`.

- [x] **Step 3: Commit**

```bash
git add scripts/check-fast.sh
git commit -m "feat(gate): add check-fast quick gate"
```

### Task 4: Pre-push hook — the first verbatim templates

**Files:**
- Create: `plugins/foundry/templates/.githooks/pre-push`
- Create: `plugins/foundry/templates/scripts/install-hooks.sh`
- Create: `.githooks/pre-push` (foundry's own copy)
- Create: `scripts/install-hooks.sh` (foundry's own copy)

- [x] **Step 1: Write the template hook**

`plugins/foundry/templates/.githooks/pre-push`:

```bash
#!/usr/bin/env bash
# foundry-template: pre-push v1
# Pre-push gate; bypass once with `git push --no-verify`.
exec "$(git rev-parse --show-toplevel)/scripts/check-fast.sh"
```

- [x] **Step 2: Write the template installer**

`plugins/foundry/templates/scripts/install-hooks.sh`:

```bash
#!/usr/bin/env bash
# foundry-template: install-hooks v1
# One-time per clone: route git hooks through .githooks/.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
hook_count="$(find .githooks -maxdepth 1 -type f | wc -l | tr -d ' ')"
[ "$hook_count" -gt 0 ] || { echo "install-hooks: no hook files in .githooks/ — nothing to install" >&2; exit 1; }
git config core.hooksPath .githooks
find .githooks -maxdepth 1 -type f -exec chmod +x {} +
echo "hooks installed (core.hooksPath=.githooks, $hook_count hook(s))"
```

- [x] **Step 3: Install foundry's own copies (byte-identical)**

```bash
mkdir -p .githooks
cp plugins/foundry/templates/.githooks/pre-push .githooks/pre-push
cp plugins/foundry/templates/scripts/install-hooks.sh scripts/install-hooks.sh
chmod +x .githooks/pre-push scripts/install-hooks.sh plugins/foundry/templates/.githooks/pre-push plugins/foundry/templates/scripts/install-hooks.sh
scripts/install-hooks.sh
```

Expected: `hooks installed (core.hooksPath=.githooks, 2 hook(s))` (count reflects files present)

- [x] **Step 4: Run the gate — byte-identity now checks real templates**

Run: `scripts/check-fast.sh`
Expected: `byte-identity: PASS` (two files compared) and `check-fast: PASS`.

- [x] **Step 5: Prove the gate discriminates (manual seeded defect)**

```bash
echo '# drift' >> scripts/install-hooks.sh
scripts/check-fast.sh; echo "exit=$?"
git checkout scripts/install-hooks.sh
```

Expected: `byte-identity: DRIFT scripts/install-hooks.sh` and `exit=1`, then clean after checkout.

- [x] **Step 6: Commit**

```bash
git add plugins/foundry/templates .githooks/pre-push scripts/install-hooks.sh
git commit -m "feat(templates): add pre-push hook and installer as first verbatim templates"
```

### Task 5: CI backstop

**Files:**
- Create: `.github/workflows/check-fast.yml`

- [x] **Step 1: Write the workflow**

```yaml
name: check-fast
on:
  push:
    branches: [main]
  pull_request:
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm install -g @anthropic-ai/claude-code
      - run: scripts/check-fast.sh
```

- [x] **Step 2: Verify locally what CI will run**

Run: `scripts/check-fast.sh`
Expected: `check-fast: PASS`. (The workflow itself is exercised on first push once a remote exists; if `claude plugin validate` needs auth in CI, gate that section on `CLAUDE_CODE_OAUTH_TOKEN` being present and record the finding here — do not delete the check.)

Finding (2026-06-10): `claude plugin validate` runs unauthenticated — probed with
`HOME="$(mktemp -d)" claude plugin validate plugins/foundry` → `✔ Validation passed`, exit 0.
No CI token gating needed.

- [x] **Step 3: Commit**

```bash
git add .github/workflows/check-fast.yml
git commit -m "ci: run the quick gate on push and pull request"
```

### Task 6: Record the gate and move the card

- [x] **Step 1: Run the full gate and capture the PASS**

Run: `scripts/check-fast.sh 2>&1 | tail -3`
Expected: `check-fast: PASS` — paste the output into the board card.

- [x] **Step 2: Update the board**

In `docs/ROADMAP.md`: plugin-skeleton card → `Done — gate recorded <date>: check-fast: PASS`; template-extraction card → `Ready`.

- [x] **Step 3: Commit**

```bash
git add docs/ROADMAP.md specs/foundry-core/tasks.md
git commit -m "chore(board): record wave 1 gate PASS, promote template extraction"
```

---

## Wave 2 — Template extraction from octant (claimed @main 2026-06-10)

Design refinement recorded at claim: template classes split into
`templates/verbatim/` (byte-checked tooling) and `templates/seeds/` (copied once,
repo-owned content) — see design §Template classes. Sources live in
`~/dev/workspace/octant`; every extraction passes the mechanisms-not-content audit
(no octant entities, terms, or standing rules in any template).

### Task 2.1: verbatim/ and seeds/ split

Move `templates/.githooks/pre-push` and `templates/scripts/install-hooks.sh` to
`templates/verbatim/...`; point `check-byte-identity.sh` at
`plugins/foundry/templates/verbatim`; update the test fixture paths to match.
Gate: byte-identity still covers both files; full test suite green.

### Task 2.2: board.sh + worktree-retire.sh (verbatim)

Copy from octant `scripts/`, add `# foundry-template:` markers, replace the one
octant-specific string (the `Octant board` echo header → `Board`); install
foundry's own copies; both runnable against foundry's ROADMAP/worktrees.
Gate: byte-identity green; `scripts/board.sh` renders foundry's dashboard.

### Task 2.3: docs.py + test_docs.py (verbatim tool + seed config) + outline/section

Port octant `scripts/docs.py`: octant-specific constants (doc globs, excluded
paths) move to a `docs/docs-config.json` seed the script loads; port
`test_docs.py`; add `outline <doc>` (heading tree) and `section <doc> <heading>`
(print one section) subcommands with tests. Foundry adopts: frontmatter on all
foundry docs, config seed present, `python3 scripts/docs.py check` + the python
tests wired into `check-fast.sh`.
Gate: docs.py check green on foundry's own docs; new subcommand tests green.

### Task 2.4: vitepress scaffold (verbatim config + seed site config)

From octant `docs/.vitepress/`: `config.ts` generalized to read title/description
from a `docs/.vitepress/site.json` seed; `package.json` + `tsconfig.json`
verbatim; sidebar generation (docs.py already emits it) wired. Foundry adopts:
its docs site builds. CI gains a docs-build step; the pre-push gate does NOT run
the build (too slow for the fast gate).
Gate: `npm ci && npm run docs:build` (or equivalent) succeeds under `docs/`.

### Task 2.5: Seed templates

Author under `templates/seeds/`, each with a `foundry-seed:` marker, generic per
the mechanisms-not-content rule: `docs/ROADMAP.md`, `docs/BACKLOG.md`,
`docs/glossary.md`, `docs/validation.md`, `docs/index.md`, `docs/README.md`,
`specs/README.md`, `features/README.md`, `.claude/rules/spec-conventions.md`,
`docs/coe-template.md`. Modeled on octant's equivalents; the glossary seed
carries the debt column, prior-art preamble, and empty entity-model section; the
ROADMAP seed carries conventions + status taxonomy + empty dashboard;
spec-conventions carries the naming/prose/prior-art rules with the
spec-reviewer dispatch. Foundry adopts the ones it lacks: `docs/index.md`,
`docs/README.md`, `docs/BACKLOG.md`, `docs/validation.md`, `specs/README.md`.
Gate: docs.py check green over the adopted files; seeds audit clean.

### Task 2.6: Record the gate, move the card

Run the full gate, record PASS on the template-extraction card, promote the
Wave 3 card (lifecycle skill + spec-reviewer) and the COE-mechanism card to Ready.

---

## Wave 3 — Skills, agent, context budget, COE closure (claimed @main 2026-06-11)

First plugin-resident prose: held hardest to Strunk & White (design §Context-economy
prose) and budget-linted. Octant sources: `.claude/skills/code/SKILL.md`,
`.claude/agents/spec-reviewer.md`. Generalization rule: the skill/agent name no
repo specifics — commands, paths, and the entity model come from the consumer
repo's AGENTS.md, glossary, and seeds (AC-3.1, AC-4.1).

### Task 3.1: `code` lifecycle skill

`plugins/foundry/skills/code/SKILL.md`, generalized from octant's: the 7-stage
checklist (Frame → Spec → Plan → Build → Verify → Docs → Finish) with gate
prohibitions; Frame routes by work size (AC-3.2); feature-file-first (AC-3.3);
prior-art naming step in the Spec stage (AC-3.4); board claim at Plan, card move +
recorded gate PASS at Finish; COE on field failures the setup permitted; the
"Don't rationalize past a gate" table; the Enhancement rule (prefer a more
specialized skill per stage). All repo specifics read from AGENTS.md/seeds.
Gate: `claude plugin validate plugins/foundry` green; prose review applied.

### Task 3.2: `spec-reviewer` agent

`plugins/foundry/agents/spec-reviewer.md`, generalized: criteria from files at
review time (repo glossary + entity model, AGENTS.md writing style) — never the
agent's priors; flags non-canonical and debt-column terms, entity-model misfits,
near-duplicate names, coined terms with no prior art or reason (AC-4.3), prose
violations; scope covers specs AND context-resident files; read-only tools.
Gate: plugin validate green; smoke-run the agent on a foundry spec.

### Task 3.3: context-budget lint

`scripts/check-context-budget.sh` (foundry-internal, not a template) + test:
fail when plugin-resident prose exceeds its budget — budgets calibrated from the
real Wave 3 files and recorded in the script. Wire into `check-fast.sh`.
Gate: TDD red→green; seeded oversize file fails the lint.

### Task 3.4: COE mechanism closure

Foundry adopts `docs/coe-template.md` from the seed; `docs/README.md` index
pointer. The promote-upstream flow and eval-accretion rule are already recorded
(design §COE, AGENTS.md); this closes the card.
Gate: `python3 scripts/docs.py check` green.

### Task 3.5: Record the gate, move the cards

Full gate PASS recorded on all three cards; bootstrap card promoted to Ready.
