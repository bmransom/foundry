> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — spawn-session worktree isolation

Waves run top to bottom. Tasks within a wave are parallel unless they name a
dependency. Each task is written test-first: the gate is the test that proves it,
and the test must fail before the change and pass after.

## Wave 1 — Spec and board

- [ ] T1: Add the `spawn-isolation` spec files and board card —
  `roadmap/specs/spawn-isolation/{requirements,design,tasks}.md`,
  `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` PASS after the spec files and
  board card land. Approval: maintainer approval recorded on the board. [US-1]
- [ ] T2: Run pre-approval `spec-review` on requirements, design, and tasks in
  fresh context; apply findings before asking for design approval. Gate: review
  report has no findings, or every finding has a recorded disposition and fix.
  [Spec README]

## Wave 2 — Isolation test harness (red)

- [ ] T3: Add `tests/fresh_session_worktree_test.sh` against a real git fixture
  (`AGENT_TMUX=/bin/echo`, `TMUX=1` to capture the launch command), modeled on
  `tests/harness_deliberation_worktree_test.sh` + `tests/fresh_session_test.sh`.
  Assert: two spawns give distinct worktree paths; distinct `foundry/fs/<id>`
  branches; the captured tmux `-c` cwd is the worktree; the source tree's
  `branch --show-current` and `status --short` are unchanged (config non-mutation is
  covered by the US-7 eval-sandbox test, T11).
  Add the seeded-defect arm: a mutant runner that writes/launches in the source dir
  must fail the test. Gate: the test fails against the current shared-tree runner
  and the mutant arm flags the seeded defect. [AC-1.1, AC-1.4, AC-1.5, AC-1.6]

## Wave 3 — Runner isolation (green)

- [ ] T4: Make the shared runner create a per-session worktree at
  `.foundry/tmp/fresh-session/<session-id>/worktree` on branch
  `foundry/fs/<session-id>` via `git worktree add -b`, base resolved
  `origin/HEAD → main → HEAD` with no fetch; write `prompt.md` to the primary
  session dir and pass it by absolute path; launch tmux/manual with cwd = the
  worktree — `plugins/foundry/scripts/spawn-fresh-session.sh` (dep T3). Gate:
  `tests/fresh_session_worktree_test.sh` PASS, including distinct worktrees,
  distinct branches, worktree cwd, and unchanged source tree. [AC-1.1, AC-1.2,
  AC-1.3, AC-1.4, AC-1.5, AC-1.6, AC-1.7]
- [ ] T5: Update `tests/fresh_session_test.sh` to assert isolation — launch cwd is
  the worktree (not the source dir) and the prompt lives under the primary session
  dir — so it stops passing under the buggy shared-tree behavior (dep T4). Gate:
  `tests/fresh_session_test.sh` PASS against the isolated runner; it would fail
  against the pre-fix runner. [AC-1.3, AC-1.4]
- [ ] T6: Implement safe failures in the runner — not a git repo refuses unless
  `FOUNDRY_SPAWN_ALLOW_NON_GIT=1` is set (and then warns on stderr that isolation is
  lost); `git worktree` unavailable exits nonzero; a failed
  `worktree add` removes the partial path, deletes the just-made `foundry/fs/*`
  branch, and does not start tmux; unknown harness or missing tmux still creates the
  worktree and prints `cd <worktree> && <command>` (dep T4). Gate: a runner test
  covers each failure path; no path falls back to the shared tree. [AC-6.1, AC-6.2,
  AC-6.3, AC-6.4]

## Wave 4 — Handoff inheritance and guardrail

- [ ] T7: Make the runner detect primary-vs-linked via
  `git rev-parse --git-dir` ≠ `--git-common-dir` and have handoff inherit the
  parent's worktree (no new worktree) when in a linked tree, promoting to a new
  worktree only from the primary tree —
  `plugins/foundry/scripts/spawn-fresh-session.sh`,
  `plugins/foundry/skills/handoff/scripts/spawn-successor.sh` (dep T4). Gate: a test
  spawns a handoff from a linked worktree and asserts no new `foundry/fs/*` branch
  and that uncommitted WIP is preserved; from the primary tree it promotes once.
  [AC-2.1, AC-2.2, AC-2.3]
- [ ] T8: Set per-session `GIT_CONFIG_GLOBAL` to a worktree-local temp config in
  the runner and document that worktrees share `.git/config`; install no `PATH` git
  shim — `plugins/foundry/scripts/spawn-fresh-session.sh` (dep T4). Gate: a test
  asserts the launched session sees `GIT_CONFIG_GLOBAL` pointing inside the session
  dir, the docs state the shared-`.git/config` caveat, and no git shim is added to
  `PATH`. [AC-3.1, AC-3.2, AC-3.3]

## Wave 5 — Deliverables and retire

- [ ] T9: Write deliverables to the primary tree, not the worktree, so retire
  cannot delete them — give each wrapper prompt an **absolute** deliverable path
  rooted at the primary project dir (`$dir`): the spec-review report
  (`plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh`, resolve
  `$report` to `$dir/.foundry/reports/spec-review/...`) and an explicit primary-tree
  draft path for the extract-skill drafter, which currently gets none
  (`plugins/foundry/skills/extract-skill/scripts/spawn-extractor.sh`) (dep T4).
  Gate: a test asserts each wrapper's prompt carries an absolute path under `$dir`
  (not relative to the worktree cwd), then spawns each, retires the worktree, and
  asserts the spec-review report under the primary tree's
  `.foundry/reports/spec-review/` and the extract-skill draft under the primary tree
  both still exist. [AC-4.1, AC-4.2]
- [ ] T10: Extend `worktree-retire.sh` with `--delete-branch` — `git branch -d` for
  `foundry/fs/*` by default, `git branch -D` under `--force`, run only after
  note-protection and worktree removal — updating the verbatim template copy and the
  self-host copy byte-identically —
  `plugins/foundry/templates/verbatim/scripts/worktree-retire.sh`,
  `scripts/worktree-retire.sh`. Gate: a retire test deletes a merged `foundry/fs/*`
  branch, refuses an unmerged branch without `--force`, and deletes it with
  `--force`; `scripts/check-byte-identity.sh` PASS. [AC-5.1, AC-5.2, AC-5.3,
  AC-5.4]

## Wave 6 — Eval sandbox

- [ ] T11: Sandbox the evals — every eval entrypoint or flow that mutates git
  config, shell (`evals/harness/*.sh`) or Python (the config-mutating flows such as
  `evals/harness/test_grade_lifecycle.py` / `grade_lifecycle.py`), runs against a
  clone/copy of the repo, never the real repo. Per the Eval sandbox section, the rule
  keys on "mutates git config," not on file extension.
  Gate: a test asserts the real repo's `.git/config` is byte-identical before and
  after an eval run, and a seeded eval fails — the seeded writer is a Python
  config-mutating flow, so the gate exercises a Python config writer (not just a
  `*.sh` script) and the rule covers both. [AC-7.1, AC-7.2]

## Wave 7 — Review and finish

- [ ] T12: Re-run `spec-review` on requirements, design, and tasks after any
  implementation-driven spec changes; apply findings. Gate: review report has no
  findings, or every finding has a recorded disposition and fix. [Spec README]
- [ ] T13: Run the canonical gate. Gate: `scripts/check-fast.sh` prints
  `check-fast: PASS` with the isolation tests, retire test, byte-identity, and eval
  sandbox landed. [US-1, T1]
