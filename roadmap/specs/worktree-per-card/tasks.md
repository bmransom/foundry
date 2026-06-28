> **Status:** Draft (2026-06-27) — pending approval.
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — worktree-per-card

## Wave 1 — the lifecycle skill

- T1 `plugins/foundry/skills/code/SKILL.md`: rewrite Plan (worktree off default branch),
  Build (checkpoint each green step), Finish (commit in worktree, ask before push,
  `Done = merged` set in the merging PR, retire worktree). Reconcile with the existing
  autonomy-dial text; keep the checklist gate lines coherent (AC-1.1, 2.1–2.3, 3.1–3.2).
- Gate: `plugin_skills_test` + context-budget check green; the skill still reads coherently
  end-to-end.

## Wave 2 — the contract docs

- T2 `AGENTS.md`: Boundaries → worktree-per-card + commit-freely + ask-before-push;
  Task tracking → `Done = merged` (AC-2.x, 3.4).
- T3 `roadmap/ROADMAP.md` board conventions + `plugins/foundry/templates/seeds/roadmap/ROADMAP.md`:
  `Done = merged`; status flow `… → In progress → Done`; `Validating` reserved;
  claim by `card/<id>` branch existence — never a default-branch claim commit; board edits
  ride the work's PR (AC-3.3, 3.4, 4.1–4.4).
- T4 `plugins/foundry/skills/bootstrap/references/generate.md`: regenerate the Boundaries
  and Task-tracking rows so a bootstrapped repo inherits the same rules.
- Gate: `check-board.py` clean; byte-identity gate green (verbatim twins unaffected).

## Wave 3 — eval + guard

- T5 `evals/harness/lifecycle-eval.sh`: update the canned prompt — runner provisions the
  worktree; commit freely, do not push (matches the new Finish).
- T6 New static doc check under `tests/` (sibling to existing shell tests): asserts the
  conventions, seed, and `AGENTS.md` carry `Done = merged` and **no** "ask before commit"
  or "Done … shipped in v" gate wording; seed a temporarily-regressed copy in the test to
  prove it discriminates.
- T7 `knowledge/log.md`: record the `Done` redefinition + the worktree-per-card policy.
- Gate: `scripts/check-fast.sh` → `check-fast: PASS`; the new doc check fails on a seeded
  regression and passes clean.
