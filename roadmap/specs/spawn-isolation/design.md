> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — spawn-session worktree isolation

## Architecture overview

Every spawned session funnels through one shared runner,
`plugins/foundry/scripts/spawn-fresh-session.sh`. The wrappers — handoff
`spawn-successor.sh`, spec-review `spawn-spec-reviewer.sh`, extract-skill
`spawn-extractor.sh` — forward a prompt on stdin and a project directory, then
delegate to the runner. The runner today writes the prompt under the caller's
directory and launches the harness with `tmux -c "$dir"`, so every session runs in
the parent's working tree.

Fix the runner once and every wrapper inherits isolation. Before writing the prompt
and launching the harness, the runner creates a dedicated git worktree for the
session and runs the harness there. Isolation is default-on: the runner replaces
the unsafe shared-tree default.

The runner reuses the broker's worktree call shape — `git -C <repo> worktree add
-b <branch> <path> <base_commit>` (`create_scratch_worktrees` in
`harness-deliberation-broker.py`).

Two collision classes motivate the work, and worktrees fix only one:

- **Working-tree and branch collisions** — concurrent sessions editing the same
  files or committing to the same branch. Worktrees fix this: each session gets its
  own checkout and its own branch.
- **Shared `.git/config` corruption** — a session running `git config --local
  core.bare true` or overwriting `[user]`. Linked worktrees share `.git/config`
  through the common git dir, so worktrees do **not** fix this. Two changes address
  it within this spec: a per-session `GIT_CONFIG_GLOBAL` guardrail (a guard, not a
  boundary) and sandboxing the evals that mutate git config so they never touch the
  real repo.

## Components

| Component | Location | Purpose |
|---|---|---|
| Shared runner | `plugins/foundry/scripts/spawn-fresh-session.sh` | Creates the per-session worktree, writes the prompt to the primary tree, launches the harness in the worktree. The single isolation chokepoint. |
| Handoff wrapper | `plugins/foundry/skills/handoff/scripts/spawn-successor.sh` | Spawns a successor; inherits the parent's worktree rather than minting a new one. |
| Spec-review wrapper | `plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh` | Spawns a reviewer; its report is written to the primary tree so retire cannot delete it. |
| Extract-skill wrapper | `plugins/foundry/skills/extract-skill/scripts/spawn-extractor.sh` | Spawns a skill drafter; inherits the shared runner's isolation and writes its draft to the primary tree so retire cannot delete it. |
| Retire script (verbatim template) | `plugins/foundry/templates/verbatim/scripts/worktree-retire.sh` | Gains `--delete-branch` for `foundry/fs/*`. |
| Retire script (self-host copy) | `scripts/worktree-retire.sh` | Byte-identical to the template copy. |
| Eval sandbox | `evals/harness/*.sh` + config-mutating Python flows (`test_grade_lifecycle.py` / `grade_lifecycle.py`) | Any eval entrypoint or flow that mutates git config — shell or Python — runs against a clone or copy of the repo. |
| Isolation test | `tests/fresh_session_worktree_test.sh` | Proves distinct worktrees and branches, an unchanged source tree, and a seeded-defect mutant runner that fails. |
| Updated runner test | `tests/fresh_session_test.sh` | Adds isolation assertions it currently lacks. |

## Worktree layout

```text
.foundry/tmp/fresh-session/<session-id>/      # primary tree, gitignored
  prompt.md                                    # written here; passed by absolute path
  gitconfig                                    # per-session GIT_CONFIG_GLOBAL target
  worktree/                                    # the only checkout the harness sees
    ...                                        # branch foundry/fs/<session-id>
```

The scaffolding — `prompt.md`, the per-session config — lives in the **primary**
session directory under gitignored `.foundry/tmp/`. Only the *checkout* lives in
`worktree/`. Keeping scaffolding outside the worktree means it survives retire, it
does not ride along on the ephemeral branch, and it does not nest a second
`.foundry/tmp/` inside the checkout. The harness launches with cwd = `worktree/`
and reads the prompt by absolute path.

The session id is the existing collision-safe
`<timestamp>-<safe-slug>-<pid>`. The branch is `foundry/fs/<session-id>`.

Provenance: `foundry/fs/` is a deliberate short branch namespace — `fs` abbreviates
the spelled-out directory concept `fresh-session` to keep ephemeral session branch
refs terse. The directory keeps the long form (`.foundry/tmp/fresh-session/`); only
the branch ref uses the abbreviation.

## Base resolution

The base is the commit `origin/HEAD` resolves to, then `main`, then `HEAD`, with no
network fetch:

```bash
base="$(git -C "$dir" rev-parse --verify -q origin/HEAD \
        || git -C "$dir" rev-parse --verify -q main \
        || git -C "$dir" rev-parse --verify -q HEAD)"
git -C "$dir" worktree add -b "foundry/fs/$session_id" "$worktree" "$base"
```

Resolving with `rev-parse`, never `fetch`, keeps parallel spawns off the network. A
fresh `-b` branch on a commit base never trips git's "branch already checked out"
guard and never checks out or mutates the primary tree.

## Handoff inheritance

A handoff successor is sequential — the parent is done — and the handoff briefing
captures *uncommitted* WIP the successor needs. A new `HEAD`-based worktree would
lose that WIP. So handoff inherits the parent's worktree instead of minting a new
one.

The runner detects whether it sits in the primary tree or a linked worktree:

```bash
git_dir="$(git -C "$dir" rev-parse --git-dir)"
common_dir="$(git -C "$dir" rev-parse --git-common-dir)"
# equal  => primary tree   => promote to a new worktree
# differ => linked worktree => reuse it; do not mint a new one
```

A fresh independent session always isolates. A handoff in a linked worktree reuses
it; a handoff in the primary tree promotes once to a new worktree, then stays.

## Guardrail: per-session GIT_CONFIG_GLOBAL

Linked worktrees share `.git/config`. The runner cannot make local-config writes
impossible without a clone, and the decided v1 is worktree-backed. The honest
guardrail:

- Set `GIT_CONFIG_GLOBAL` to `.foundry/tmp/fresh-session/<session-id>/gitconfig`
  for the spawned session, so a session's global-config writes land in a throwaway
  file.
- Document plainly that worktrees share `.git/config`; `git config --local` and
  `core.bare` writes still reach the shared file, and this guardrail does not
  isolate it.
- Install **no** `PATH` git shim. A shim is brittle, admits it is not a real
  boundary, and gives false assurance. Full `.git/config` isolation requires a
  clone, deferred below.

## Deliverables outlive the worktree

Two spawned flows produce artifacts that must survive retire: spec-review writes a
report, and extract-skill writes a skill draft. Spec-review writes its report to
`.foundry/reports/spec-review/...`; the retire script's note regex
`(.*followup|.*handoff|.*scratch|.*notes|TODO)` does not match `report` or `draft`,
so `git worktree remove` would drop either silently.

Deliverables that must outlive the worktree are written to the **primary** tree.
The mechanism is an **absolute** deliverable path in each wrapper's prompt, rooted
at the primary project directory (`$dir`), not a path relative to the harness cwd
(which after isolation is the worktree).

- The spec-review wrapper resolves `$report` to an absolute path under the primary
  tree's `.foundry/reports/spec-review/` (`$dir/.foundry/reports/spec-review/...`)
  and passes that absolute path in the prompt. Today it passes `$report` relative
  to cwd (`spawn-spec-reviewer.sh`).
- The extract-skill wrapper specifies an explicit primary-tree draft path —
  absolute, under `$dir` — in its prompt. Today it gives the drafter no output path
  at all (`spawn-extractor.sh`), so the draft lands wherever the agent chooses,
  inside the worktree.

Retiring the worktree then cannot delete either.

## Retire with safe branch deletion

`worktree-retire.sh` already protects un-promoted gitignored notes before removing a
worktree. Extend it with `--delete-branch`:

- `--delete-branch` deletes a `foundry/fs/*` branch with `git branch -d` after
  removing the worktree — the merge-safe delete that refuses an unmerged branch.
- `--delete-branch --force` uses `git branch -D`.
- Branch deletion runs only after the existing note-protection and worktree-removal
  steps succeed.

Both copies — the verbatim template
`plugins/foundry/templates/verbatim/scripts/worktree-retire.sh` and the self-host
copy `scripts/worktree-retire.sh` — change together and stay byte-identical
(modulo the version-marker line). The byte-identity gate `check-byte-identity.sh`
enforces this; the change is behavior-changing, so it ships with eval coverage.

## Error handling

Failures stop loudly. The runner never falls back to the shared tree.

| Failure | Handling |
|---|---|
| Caller dir is not a git repo | Refuse and exit nonzero unless `FOUNDRY_SPAWN_ALLOW_NON_GIT=1` is set; never spawn in place. |
| `git worktree` unavailable | Exit nonzero (matches the harness-deliberation preflight stance). |
| `git worktree add` fails | Remove the partial worktree path; delete the `foundry/fs/*` branch only if `git rev-parse --verify -q` confirms it exists (the failure may precede branch creation, so an unconditional delete would itself error and mask the original failure); do not start tmux. |
| Unknown harness or missing tmux | Still create the worktree; print `cd <worktree> && <command>`. |
| Branch not fully merged on `--delete-branch` | `git branch -d` refuses; report the unmerged branch; `--force` deletes with `-D`. |

The non-git opt-out is `FOUNDRY_SPAWN_ALLOW_NON_GIT=1`. When it lets a spawn
proceed, the runner stays loud: it prints a stderr warning naming the lost
isolation — the session runs in place in a non-git directory with no worktree and
no branch — before launching.

## Eval sandbox

A `.git/config` corruption was recorded during development:
`.agent/handoff/HANDOFF.md` notes a concurrent session that flipped `core.bare` to
`true` and overwrote `[user]` to `foundry-eval`/`eval@foundry.local`. The incident
was not reproducible from foundry's own test suite in isolation; the `foundry-eval`
identity literal lives only in `evals/harness/test_grade_lifecycle.py`, so the
likely writer was a concurrent eval run mutating git config inside the real repo.
Worktrees alone do not fix this class: linked worktrees share the corrupted file.

To prevent that risk, any eval entrypoint or flow that mutates git config — shell
(`evals/harness/*.sh`) or Python — must operate on a clone or copy of the repo,
never the real repo. The scope explicitly covers the implicated Python flow: the
`foundry-eval` identity literal lives in `test_grade_lifecycle.py`, so the
`*.sh` glob alone would leave the actual writer uncovered; the rule keys on "mutates
git config," not on file extension. A run that fails midway leaves the real
`.git/config` untouched. This is a sibling change in the same spec because it closes
the config-corruption class that worktree isolation alone leaves open.

## Testing strategy

Each test carries a seeded defect the gate catches. Green-ness is not the
evaluator; discrimination is.

`tests/fresh_session_worktree_test.sh` (new) runs against a real git fixture with
`AGENT_TMUX=/bin/echo` and `TMUX=1` so the launch command is captured, modeled on
`harness_deliberation_worktree_test.sh` and the existing `fresh_session_test.sh`. It
asserts:

1. Two spawns produce **distinct** worktree paths under
   `.foundry/tmp/fresh-session/<id>/worktree`.
2. Two spawns produce **distinct** `foundry/fs/<id>` branches.
3. The captured tmux `-c` cwd is the worktree, not the source dir.
4. The source tree's `branch --show-current` and `status --short` are unchanged
   after both spawns. (Config non-mutation is exercised by the eval-sandbox test
   under US-7, where a config-mutating mutant makes it discriminate; a worktree
   spawn never writes `core.bare`, so a `core.bare` check here catches no modeled
   failure mode.)
5. **Seeded defect** — a mutant runner that writes the prompt and launches in the
   source dir (the pre-fix behavior) makes the test fail.

The test notes the one thing it cannot cover under worktree-only isolation: two
*running* agents corrupting shared `.git/config`. That class is closed by the eval
sandbox, not by the worktree test.

`tests/fresh_session_test.sh` (updated) gains isolation assertions: the launch cwd
is the worktree, not the source dir, and the prompt lives under the primary session
dir. It must stop passing under the buggy shared-tree behavior.

Retire coverage: a test creates a `foundry/fs/*` worktree, runs
`worktree-retire.sh --delete-branch`, and asserts the worktree is gone and the
branch deleted; an unmerged branch without `--force` refuses; the byte-identity gate
proves the two retire copies match.

Eval-sandbox coverage: a test (or the eval driver itself) asserts the eval runs
against a clone/copy and the real repo's `.git/config` is byte-identical before and
after; a seeded eval that writes to the real repo's config fails. The seeded writer
is a Python config-mutating flow (e.g. `test_grade_lifecycle.py`), since that is the
recorded failure mode — the `foundry-eval` identity literal that corrupted
`.git/config` lives there, not in any `*.sh` script.

## Deferred dissent — worktree-backed vs clone-backed isolation

Worktree-backed isolation fixes the working-tree and branch collision class but not
the `.git/config` corruption class, because linked worktrees share `.git/config`
through the common git dir. Full isolation of that class requires per-session
clone-backed isolation (`git clone --local`, a separate `.git/config`), which is
heavier and changes retire from `git worktree remove` to clone teardown.

The decided v1 is worktree-backed isolation, with the config-corruption class closed
for evals by the sandbox (US-7) and guarded for live sessions by per-session
`GIT_CONFIG_GLOBAL` plus honest documentation (US-3). Clone-backed isolation is
recorded here as the deferred alternative for full config isolation; this spec does
not reopen the fork.

Provenance: the worktree-vs-clone decision and the PATH-shim rejection are grounded
in the si-spec harness deliberation finals,
`.foundry/tmp/harness-deliberation/si-spec/turns/0001-codex/final.md` and
`.foundry/tmp/harness-deliberation/si-spec/turns/0002-claude/final.md`.
