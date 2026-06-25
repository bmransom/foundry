# Generate — the per-stack cookbook

Every command below is the stack default; detected and interview-confirmed commands win.

## AGENTS.md skeleton

Write the sections in this order. AGENTS.md loads into every session: hold it
to the Writing style it declares.

| Section | Content |
|---|---|
| Intro (no heading) | What the repo is, what it ships, who consumes it — ≤ 4 lines, from the interview description. |
| `## Commands` | A code block of real commands, the canonical gate (`scripts/check-fast.sh`) first; then one line: pre-push runs the same gate (`scripts/install-hooks.sh` once per clone; bypass once with `git push --no-verify`). |
| `## Boundaries` | **Never** — repo-specific prohibitions from the interview and inspection. **Always** — "Use the `knowledge/glossary.md` vocabulary in records, APIs, and docs — it is the contract."; "Before coining a canonical name (glossary term, public type or field, config knob), search the prior art and record provenance in the glossary."; "Stage explicit paths, never `git add -A`." **Ask first** — "Commit or push. Branch first if on the default branch." |
| `## Writing style` | The block below, verbatim. |
| `## Testing` | The repo's test-scoping commands; integration over mocks; the feature-file rule: "New feature → add a Scenario; enhancement → update it; refactor → leave it." |
| `## Contracts` | Only when an API surface exists — §Contracts. |
| `## Logging` | Apps and services only — §Logging. |
| `## Task tracking` | `roadmap/ROADMAP.md` is the board; claim a card by owner; `Done` requires a recorded gate PASS; specs live in `roadmap/specs/<feature>/`; ideas in `roadmap/BACKLOG.md`. |
| `## Deeper docs` | One line: `knowledge/README.md` indexes everything · glossary · validation · specs. |

Writing-style block:

> The standard is Strunk & White: omit needless words; use the active voice;
> make definite assertions. Lead with the point; one idea per sentence;
> concrete commands, paths, and names; say it once and link to depth. Prefer a
> table, list, or code block when denser than a sentence. Context-resident
> prose (AGENTS.md, rules, skills) loads into every session — every needless
> word costs tokens each time it loads; cut hardest there.

## Gate wiring — check-fast.sh

Assemble from: the detected stack rows below (only tools the repo actually
configures), the interview-confirmed commands, and always
`python3 scripts/knowledge.py check` and the feature-runner command.

| Stack | Commands |
|---|---|
| Rust | `cargo clippy --workspace --all-targets -- -D warnings` · `cargo test --workspace --quiet` (scope to the big crate when slow: `cargo test -p <crate> --lib --quiet`) · `cargo build --workspace` |
| Python | `ruff check .` · `pytest -q` |
| TS/JS | `npx tsc --noEmit` · `npx vitest run` or `npx jest` (whichever is configured) · `npx eslint .` when an eslint config exists |

Shape:

```bash
#!/usr/bin/env bash
# The quick gate: lock-free; runs from .githooks/pre-push and CI.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

echo "== lint"
<stack lint commands>

echo "== tests"
<stack test commands, including the feature runner>

echo "== knowledge"
python3 scripts/knowledge.py check

echo "check-fast: PASS"
```

`scripts/verify.sh` exists only when an expensive validation does (long
benchmark, full suite): it runs `check-fast.sh` plus the heavy step behind the
machine-global lock from §Isolation.

After filling the seed concepts, regenerate the listing: `python3 scripts/knowledge.py
index` writes `knowledge/index.md` (the OKF directory listing + site home). The gate's
`knowledge check` fails if it is stale.

## BDD wiring

One runner per production entrypoint the repo actually has. Steps drive the
production entrypoint — the built binary, the installed console script, the
served app — never an internal function, never a mock.

| Stack | Runner | Wiring |
|---|---|---|
| Rust | cucumber-rs | `cucumber` (+ `tokio`) as dev-dependencies; `[[test]] name = "acceptance"` with `harness = false`; `tests/acceptance.rs` loads `features/` and shells the built binary |
| Python | pytest-bdd | `pytest-bdd` dev dependency; `tests/test_acceptance.py` calls `scenarios("../features")`; steps invoke the entrypoint via `subprocess` |
| TS/JS | cucumber-js | `@cucumber/cucumber` dev dependency (+ `ts-node` registered in the cucumber config for TS); steps spawn the bin or hit the served endpoint |

Walking-skeleton Scenario — name the feature file after the repo's core verb
(`features/README.md` explains the two contract kinds):

```gherkin
Feature: <core capability>
  Scenario: the production entrypoint responds
    Given the <entrypoint> is built and available
    When it is invoked with <a trivial valid input>
    Then it exits cleanly with <the expected output>
```

## Contracts — interview named an API surface

| Stack | Mapping |
|---|---|
| TS | zod + orpc, or ts-rest |
| Python | pydantic |
| Rust | serde + schemars, or utoipa for HTTP |

Section rule text: write the schema first; derive types from it — never
parallel hand-written types; validate at every boundary (parse, don't trust);
feature Scenarios exercise the contract through the production entrypoint.

## Logging — repo shape is app or service

A plain CLI gets no Logging section: its unit of work ends at the process
boundary, and its structured output IS its result.

| Stack | Library |
|---|---|
| Rust | `tracing` + JSON subscriber |
| Python | `structlog` |
| TS/Node | `pino` |

Section rule text: structured key-value events, never prose interpolation; one
**wide event** per unit of work — the interview named it — carrying identity,
release metadata, execution cost, and decision inputs; trace/span correlation
IDs on every record; field names come from `knowledge/glossary.md` — the log schema
is the glossary on the wire.

Wire the library and emit one working wide event at the end of the unit of
work in the production entrypoint, so the walking skeleton exercises it.

## Isolation — by interview and repo shape

| Repo shape | Pattern |
|---|---|
| Service/app, parallel agents | `scripts/agent-env.sh`: per-worktree `.env`, deterministic free ports; testcontainers wiring for integration tests |
| Resource-heavy single-host gate | machine-global mkdir-lock in `verify.sh`, stale-lock reclaim |
| Library or CLI / solo | `worktree-retire.sh` + the explicit-paths staging rule only |

## CI workflow

`.github/workflows/check-fast.yml`, two jobs — gate and docs-build — on push
and pull_request:

```yaml
name: check-fast
on:
  push:
    branches: [<default branch>]
  pull_request:
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - <stack toolchain setup + dependency install: dtolnay/rust-toolchain / setup-python + pip install -e '.[dev]' / setup-node + npm ci>
      - run: scripts/check-fast.sh
  docs-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm, cache-dependency-path: knowledge/package-lock.json }
      - run: npm ci
        working-directory: knowledge
      - run: npm run build
        working-directory: knowledge
```

Gitignore the docs build artifacts (`knowledge/node_modules/`,
`knowledge/.vitepress/cache/`, `knowledge/.vitepress/dist/`,
`knowledge/.vitepress/sidebar.generated.json`); track `knowledge/package-lock.json`.

## vocab-lint — glossary debt column has entries

`scripts/vocab-lint.sh`: read the terms from the "Replaces (now debt)" column
of `knowledge/glossary.md` at run time (the glossary stays the single source). Lint
**prose surfaces only** — markdown (`*.md`) under the directories the polarity answer
names (`knowledge/` and `roadmap/specs/`; plus code identifiers for an excluding
engine) — and EXCLUDE generated and dependency trees: `node_modules/`, `dist/`,
lockfiles, and the VitePress build output (`.vitepress/cache`, `sidebar.generated.json`).
This matters: a recursive grep over `knowledge/` also reads `package-lock.json` and the
docs-site build, where a debt term hides inside a dependency name (case-insensitive `AI`
matches `sponsors/ai`) and yields a false failure — scoping to `*.md` prose and
excluding generated trees prevents it. Exclude the glossary itself — its debt column
lists every term. Match whole words, case-insensitively; fail on any hit:

Keep the script portable to Bash 3.2, which `/usr/bin/env bash` resolves to on
macOS. Do not use Bash 4-only helpers such as `mapfile` or `readarray`; stream
terms with `while read` or `awk`.

```
vocab-lint: DEBT <term> <path>:<line>
```

End with `vocab-lint: PASS`; wire it into `check-fast.sh`.
