# Foundry core — tasks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** Wave 1 done (2026-06-10); Waves 2–7 scope-locked, each planned at claim time per the lifecycle Plan stage — tracked on the [board](../../docs/ROADMAP.md). Wave 1 code blocks below were synced with the post-review fixes (marketplace validate in the gate, EMPTY-TEMPLATE check, no-tests guard, install-hooks hook-count guard) so the plan remains a faithful account of what shipped.

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
