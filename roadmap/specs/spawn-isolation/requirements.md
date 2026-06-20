> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — spawn-session worktree isolation

Concurrent sessions collide on the working tree and the shared branch; a session
that mutates `.git/config` corrupts the repo. The cause: every spawned session —
handoff successor, spec reviewer, skill extractor — runs in the same working tree
as its parent, because the shared fresh-session runner
`plugins/foundry/scripts/spawn-fresh-session.sh` writes the prompt under the
caller's directory and launches the harness with `tmux -c "$dir"`. Isolation must
be the default, and the flows that mutate git config must run against a copy, not
the real repo.

## User stories

### US-1: Isolate every spawned session in its own worktree

As a Foundry user, I want each spawned session to run in its own git worktree on
its own branch so concurrent sessions never collide on the working tree, the
checked-out branch, or each other's edits.

Acceptance criteria:

- AC-1.1 WHEN the shared runner spawns a session, THE SYSTEM SHALL create a git
  worktree at `.foundry/tmp/fresh-session/<session-id>/worktree` on branch
  `foundry/fs/<session-id>` via `git worktree add -b`.
- AC-1.2 WHEN the runner resolves the worktree base, THE SYSTEM SHALL use
  `origin/HEAD`, then `main`, then `HEAD`, resolved to a commit with no network
  fetch, and SHALL NOT checkout or mutate the primary tree.
- AC-1.3 WHEN the runner writes the prompt, THE SYSTEM SHALL write it under the
  primary session directory and pass it to the harness by absolute path.
- AC-1.4 WHEN the runner launches tmux or prints a manual command, THE SYSTEM
  SHALL set the working directory to the worktree, not the caller's directory.
- AC-1.5 WHEN two sessions spawn, THE SYSTEM SHALL give them distinct worktree
  paths and distinct `foundry/fs/<session-id>` branches.
- AC-1.6 WHEN a session spawns, THE SYSTEM SHALL leave the source tree's current
  branch and `git status` unchanged. (Config non-mutation is covered by US-7, where
  a config-mutating mutant exercises it.)
- AC-1.7 WHEN the runner spawns a session, THE SYSTEM SHALL isolate by default;
  isolation SHALL NOT require an opt-in flag.

### US-2: Inherit the parent's worktree on handoff

As a handoff successor, I want to continue in my parent's worktree rather than a
fresh one so I keep the uncommitted work the parent left for me.

Acceptance criteria:

- AC-2.1 WHEN a handoff spawns from a linked worktree (`git rev-parse --git-dir`
  differs from `--git-common-dir`), THE SYSTEM SHALL reuse that worktree and SHALL
  NOT mint a new one.
- AC-2.2 WHEN a handoff spawns from the primary tree (`--git-dir` equals
  `--git-common-dir`), THE SYSTEM SHALL create a new worktree for the successor
  (promoting the work out of the primary tree).
- AC-2.3 WHEN a handoff reuses the parent's worktree, THE SYSTEM SHALL preserve
  that worktree's uncommitted changes for the successor.

### US-3: Guard against shared git-config without a false boundary

As a Foundry maintainer, I want a guardrail that reduces accidental shared-config
writes and documents the residual risk honestly, not a shim that pretends to be a
security boundary.

Acceptance criteria:

- AC-3.1 WHEN the runner launches a session, THE SYSTEM SHALL set
  `GIT_CONFIG_GLOBAL` to a worktree-local temporary config file for that session.
- AC-3.2 WHEN the runner documents isolation, THE SYSTEM SHALL state that
  worktrees share `.git/config` and that this guardrail does not isolate it.
- AC-3.3 WHEN the runner isolates a session, THE SYSTEM SHALL NOT install a `PATH`
  git shim.

### US-4: Keep deliverables alive past worktree retirement

As a spec reviewer, I want my report written to the primary tree so retiring my
worktree cannot delete it.

Acceptance criteria:

- AC-4.1 WHEN a spawned flow produces a deliverable that must outlive the worktree
  — a spec-review report or an extract-skill draft — THE SYSTEM SHALL write it to
  the primary tree, not the worktree.
- AC-4.2 WHEN a worktree is retired, THE SYSTEM SHALL NOT delete a deliverable
  written under AC-4.1.

### US-5: Retire a session worktree and its branch safely

As a Foundry user, I want to retire a session worktree and delete its branch
without losing un-promoted work.

Acceptance criteria:

- AC-5.1 WHEN `worktree-retire.sh --delete-branch` runs on a `foundry/fs/*`
  worktree, THE SYSTEM SHALL delete the branch with `git branch -d` after removing
  the worktree.
- AC-5.2 WHEN `--delete-branch` runs without `--force` and the branch is not fully
  merged, THE SYSTEM SHALL refuse the delete and report the unmerged branch.
- AC-5.3 WHEN `--delete-branch --force` runs, THE SYSTEM SHALL delete the branch
  with `git branch -D`.
- AC-5.4 WHEN the `worktree-retire.sh` template changes, THE SYSTEM SHALL keep the
  verbatim template copy and the self-host copy byte-identical.

### US-6: Fail safely, never fall back to the shared tree

As a Foundry maintainer, I want isolation failures to stop loudly so a spawn never
silently runs in the shared tree.

Acceptance criteria:

- AC-6.1 WHEN the caller directory is not a git repo, THE SYSTEM SHALL refuse to
  spawn unless `FOUNDRY_SPAWN_ALLOW_NON_GIT=1` is set, and SHALL NOT spawn in
  place.
- AC-6.2 WHEN `git worktree` is unavailable, THE SYSTEM SHALL exit nonzero.
- AC-6.3 WHEN `git worktree add` fails, THE SYSTEM SHALL remove the partial
  worktree path and the `foundry/fs/<session-id>` branch if either was created
  (deleting the branch only when `git rev-parse --verify -q` confirms it exists, so
  cleanup never errors when the failure preceded branch creation), and SHALL NOT
  start tmux.
- AC-6.4 WHEN the harness is unknown or tmux is missing, THE SYSTEM SHALL still
  create the worktree and print `cd <worktree> && <command>`.

### US-7: Sandbox the evals that mutate git config

As a Foundry maintainer, I want every eval or flow that mutates git config to run
against its own clone or copy so a run can never corrupt the real repo's
`.git/config`.

Acceptance criteria:

- AC-7.1 WHEN any eval entrypoint or flow that mutates git config runs — shell
  (`evals/harness/*.sh`) or Python (the config-mutating flows such as
  `evals/harness/test_grade_lifecycle.py` / `grade_lifecycle.py`) — THE SYSTEM SHALL
  operate on a clone or copy of the repo, never the real repo.
- AC-7.2 WHEN a sandboxed eval finishes or fails, THE SYSTEM SHALL leave the real
  repo's `.git/config` unchanged.

## Out of scope

- Clone-backed per-session isolation. Worktree-backed isolation is the decided v1;
  full `.git/config` isolation via `git clone --local` is deferred (design records
  this as deferred dissent).
- A `PATH` git shim or any mechanism presented as a security boundary.
- Auto-retiring a session worktree; retirement stays an explicit step.
- Merging or promoting a `foundry/fs/*` branch into the source line.
- Changing the harnesses, prompts, or output contracts of the spawned sessions.
