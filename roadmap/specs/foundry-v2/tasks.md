---
title: foundry-v2 tasks
description: Implementation plan in waves — skeleton, driver, routing + codex, gate + doctor + pinned run, materializer, eval + review surfaces.
---

> **Status:** In progress (2026-07-02) — tracked on the [board](../../ROADMAP.md).

# foundry-v2 — tasks

Tasks within a wave are independent unless a task names an earlier one (T7 integrates
T4–T6; T8 extends T7); the board's `Depends on` column is the constraint graph, wave
numbers the default schedule (Wave 5 splits into cards 5a/5b). Every task is
TDD — the test lands red first — and names the gate that proves it. Implementers: read
`design.md` first; all schemas (config, adapter, ledger event) are normative there.

## Wave 0 — package skeleton (card `v2-skeleton`)

- **T1 — package + CI wiring.** `pyproject.toml` at repo root (name `foundry`,
  `requires-python = ">=3.11"`, console script `foundry = foundry.cli:main`, pytest as
  dev dependency, src layout). `src/foundry/cli.py` with argparse dispatch and
  `foundry --version`. Add `uv run pytest -q` as a step in `scripts/check-fast.sh`.
  Test: `tests/test_cli.py::test_version`. Gate: `check-fast: PASS` with the pytest step
  live.
- **T2 — config.** `src/foundry/config.py`: load `.foundry/config.toml` (tomllib) +
  `.foundry/manifest.json`; `Config.route_for(stage)` with precedence flag > stage >
  default > shipped defaults (design D3); missing file → shipped defaults; malformed →
  one-line error naming the key. Tests: `tests/test_config.py` (precedence table,
  missing/malformed cases). Gate: pytest green.
- **T3 — ledger.** `src/foundry/ledger.py`: event dataclasses (design D4 field set),
  `RunLedger.append/events/last_boundary`, run-id generation, price table with
  `prices_updated`. Unknown model → `cost_usd: null`. Tests: `tests/test_ledger.py`
  (append-only, resume boundary, cost math, unknown model). Gate: pytest green.

## Wave 1 — driver, claude-code only (card `v2-driver`)

- **T4 — adapter loader + claude-code adapter.** `src/foundry/adapters/__init__.py`
  (TOML load, argv template expansion — reject any template containing shell
  metacharacters), `claude_code.toml`, `parsers.py::parse_claude_stream_json` →
  `StageResult`. Conformance fixture: a recorded real `claude -p --output-format
  stream-json` transcript under `tests/fixtures/adapters/claude-code/`. Tests:
  `tests/test_adapters.py`. Gate: pytest green incl. fixture parse.
- **T5 — state machine.** `src/foundry/driver/machine.py` + `stages.py`: stage graph per
  design D1 (kinds, gates as `GateCheck` callables, retry caps, review round ceiling 20,
  `run_halted` events, entry map for feature/bug-fix/refactor/enhancement paths, stage
  hooks per AC-1.9 — `.foundry/hooks/<stage>.{pre,post}.sh` run at boundaries,
  `hook_evaluated` events). Tests: `tests/test_machine.py` with a `FakeAdapter` — assert
  a failed gate blocks transition, retry_cap halts, review loops back to build, entry
  maps skip correctly, a failing pre hook blocks entry and a failing post hook fails the
  gate. Gate: pytest green.
- **T6 — stage rubrics + prompts.** Extract each judgment stage's rubric (design D8)
  from the v1 skills into `src/foundry/rubrics/<stage>.md` — intent, invariants, output
  contract; orchestration stripped (the driver owns worktree/board/commit sequencing).
  Sources: spec ← `code` §1 + `spec-review`; plan ← `code` §2; build ← `code` §3;
  knowledge ← `knowledge`; review ← `code-review`. `prompts.py` composes rubric(s) +
  card context (id, spec paths, autonomy level) per the stage→rubric map in `stages.py`
  (advisory skills composed by reference; when wiring the map, audit each advisory
  skill for session/orchestration assumptions that read wrong in a headless stage
  prompt — flag them, method content unchanged per Out of scope). The spec rubric
  requires design.md's **Public surface** and **Invariants** sections and declares
  `open_questions` in its output contract (AC-10.4/10.5); bump the specs-readme seed to
  v4 with the same two sections, mirror this repo's `roadmap/specs/README.md` copy, and
  add a discriminating eval case (a spec missing either section must be flagged).
  Tests: golden-file prompts under `tests/fixtures/prompts/`, including a seeded
  orchestration-verb rubric that must fail. Gate: pytest green.
  T6 audit results (2026-07-02): `extract-skill` rides the fresh-session/tmux runner and
  says "this session" / "ask the user" (Wave-4 reshape confirmed); `performance`
  sequences lifecycle stages and presumes its own workspace setup; `debug`'s relative
  `references/` links break when composed; naming/design/structure carry only mild
  "during spec review, ask…" framing — acceptable as method content. The seed eval case
  needs a live-LLM reviewer run (no deterministic slot in `evals/`); the requirement is
  pinned mechanically in `tests/test_prompts.py` meanwhile.
- **T7 — `foundry run` end-to-end.** Wire cli → board resolution (parse the ROADMAP card
  table; unknown id → error listing near matches) → worktree create (`git worktree add -b
  card/<id> wt/<id> origin/<default>`, reuse if present) → machine → ledger. First seed
  `features/` in this repo from the package seed template (`src/foundry/templates/seeds/features/`),
  then write the `features/` Scenario for `foundry run` before the code. Smoke: drive a scripted
  fake-adapter run of a bug-fix path on a pytest repo fixture (design §New vocabulary)
  under `tests/fixtures/repos/`;
  assert ledger event sequence and no default-branch commits (AC-1.8). Gate:
  `check-fast: PASS` + smoke test green.
- **T8 — interrupt/resume + interactive.** `--resume <run-id>` (ledger `last_boundary`),
  `--interactive` (adapter `[interactive]` command in the stage worktree, gate evaluated
  on exit). Tests: kill mid-stage → resume continues at boundary; interactive path unit-
  tested with a stub command. Gate: pytest green.

## Wave 2 — routing + codex (card `v2-routing-codex`)

- **T9 — codex adapter.** `codex.toml` (headless `codex exec`, effort via `-c
  model_reasoning_effort=`), `parse_codex_jsonl`, recorded conformance fixtures. Tests
  mirror T4. Gate: pytest green.
- **T10 — routing live.** Thread `Route` through machine → adapter; ledger records
  resolved (harness, model, effort); `--harness/--model/--effort` CLI flags; effort
  omitted where unsupported (AC-3.3). Live smoke (maintainer-run): one two-stage run
  routing build→claude-code, review→codex; paste the ledger lines into the PR. Gate:
  pytest green + pasted smoke ledger.

## Wave 3 — gate, doctor, pinned run (card `v2-gate-doctor`) — convention break

- **T11 — gate suite.** Port `check-board.py`, `prose-lint.py`, `knowledge.py check`
  into `src/foundry/gate/{board,prose,knowledge}.py`; `suite.py` runs them +
  `[gate].commands`, last line `gate: PASS|FAIL`. Parity test: suite output vs v1 script
  output on this repo's tree and on a seeded-defect fixture (each check must fail its
  defect — discrimination, not green-ness). Gate: parity + discrimination tests green.
- **T12 — doctor.** `src/foundry/doctor.py` per AC-6.1 (config/pin, manifest hashes,
  adapter availability + conformance, hooks wired, board schema); one finding + fix per
  failure, exit non-zero on findings. Tests: pytest repo fixtures, one per defect. Gate:
  pytest green.
- **T13 — pinned-run migration (conv break).** Migration `m005_pinned_run.py` (or next
  free number): delete vendored gate-script templates, rewrite `.githooks/pre-push` + CI
  workflow to the pinned `uvx` command (design D5), stamp new convention version; update
  the migration registry head; retire the `# foundry-gate-tool:` marker lint. Apply to
  this repo in the same PR by invoking the module's `apply()` directly (`foundry update`
  wires it in Wave 4); `check-fast.sh` becomes this repo's `[gate].commands` entry
  (design D5). First pin: the migration PR pins the merge-base commit SHA; retag to the
  release tag after merge (pins are tags thereafter). Eval: migration fixture proves a
  v1 repo migrates green and re-run is a no-op. Gate: `gate: PASS` via the pinned
  pre-push + migration eval green.

## Wave 4 — materializer (card `v2-materializer`)

- **T14 — templates into the package.** Move `plugins/foundry/templates/` →
  `src/foundry/templates/`; move the self-host byte-identity check to the new path in
  the same PR (TR-2). Gate: `check-fast: PASS`.
- **T15 — `foundry bootstrap`.** `materializer/bootstrap.py`: interview (judgment call
  via adapter, or `--answers <json>` for headless/eval use) → deterministic materialize →
  manifest stamp → verify. Idempotency test: second run over pristine writes nothing.
  Smoke: bootstrap a scratch repo end-to-end. Gate: pytest + smoke green.
- **T16 — `foundry update` + migrations.** `materializer/update.py`: hash-compare,
  customized files flagged never overwritten, apply `migrations/m*.py` from repo's
  convention version; port the conv 2–4 playbooks as the first modules (the pinned-run
  module landed as code in T13). Delete the v1 prose update mechanics, the tmux spawn
  scripts, the convergence-hook scripts that ride them, and the `code`, `handoff`,
  `spec-review`, `code-review`, and `knowledge` skill files (their judgment cores live
  in T6's rubrics; the ledger + `--resume` replace handoff); reshape `extract-skill`
  off the fresh-session runner so no kept skill references a deleted script (TR-3,
  design D7/D8); repoint the reviewer/lifecycle evals at the rubrics. Eval: v1-layout
  fixture migrates to current green. Gate: pytest + migration eval green.

## Wave 5 — eval matrix + PR review (cards `v2-eval-matrix`, `v2-pr-review`)

- **T17 — eval matrix runner.** `foundry eval --matrix
  claude-code:claude-opus-4-8,codex:gpt-5.5 …`: run eval fixtures per cell via the
  driver's headless path; per-cell pass/fail + cost table; discrimination grading
  (AC-8.2). Gate: matrix run on one fixture pasted into the PR.
- **T18 — PR-review runner.** `review/pr.py`: `gh pr checkout` into an isolated
  worktree, run the review stage (reviewer + refuter convergence), post findings as
  anchored PR comments via `gh api`; never approve/merge (AC-9.2). Live smoke on a
  scratch PR in this repo. Gate: pytest green + smoke PR link.

## Deferred (explicitly not scheduled)

Per-model skill compilation variants; harness-deliberation on the driver; third-harness
adapter; external telemetry. Each waits on ledger/eval data showing the need.

Interactive marker capture (found in T8): under `--interactive`, stdio is inherited, so
spec/review marker gates cannot see their `SPEC_REVIEW:`/`CODE_REVIEW:` last line and
FAIL deterministically (never auto-pass). Candidate fixes when scheduled: tee/PTY
capture, or a headless grading call over the worktree after the session exits.
Command-shaped gates work fully interactive.
