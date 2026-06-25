> **Status:** Revising (2026-06-24) — convergence cycle. Tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — code review

Waves run top to bottom. Tasks within a wave are parallel unless they name a
dependency. Every task names the gate that proves it and the AC it satisfies.

**Waves 1–8 (T1–T17) are the shipped v1 baseline** — the single-pass reviewer,
refuter spawn, lifecycle Review stage, seeded fixture, and A/B eval already merged
to `main`. **Waves 9–14 (T18+) are the convergence-cycle revision**, which
supersedes: v1's three-round outer cap (→ T22, 20 rounds), its fire-and-forget
refuter wiring (→ T19, synchronous), its `git merge-base main HEAD` diff-base
default (→ T23, the shared resolver), and its `--skip-permissions` forwarding to the
read-only reviewer/refuter (→ T23, the bypass reaches write-capable spawns only).
Where a Wave 1–8 task names the old behavior, the cited revision task is authoritative.

## Wave 1 — Spec and board

- [ ] T1: Add `code-review` spec files and board card —
  `roadmap/specs/code-review/{requirements,design,tasks}.md`,
  `roadmap/ROADMAP.md`. Gate: `scripts/check-fast.sh` prints `check-fast: PASS`
  after the spec files and board card land. Approval: maintainer approval
  recorded on the board. [AC-10.3]
- [ ] T2: Run pre-approval `spec-review` on requirements, design, and tasks in
  fresh context; apply findings before design approval. Gate: review report has
  no findings, or every finding has a recorded disposition and fix. [Spec README]

## Wave 2 — Static skill test (red)

- [ ] T3: Write `tests/code_review_skill_test.sh` mirroring
  `tests/spec_review_skill_test.sh` — assert frontmatter `name: code-review`,
  description starts with `Use when`, the SKILL reads `knowledge/glossary.md` and
  the `AGENTS.md` contract, prefers fresh context, names
  `.foundry/reports/code-review/`, exposes `scripts/spawn-code-reviewer.sh`, the
  wrapper is executable, `--print-harness` honors `AGENT_HARNESS=codex` and exits
  without spawning (no report written, no session launched), a
  `--dry-run` carries harness + spec dir + diff range + fresh-session prompt path
  + report path, `--dry-run --skip-permissions` (and its `--yolo` alias) passes
  the permission bypass through to the shared runner, a `--dry-run` without
  `--base` shows the `git merge-base main HEAD` default diff range while
  `--dry-run --base <ref>` shows the overridden range, and `code/SKILL.md`
  delegates the Review stage. Gate: the test exists, is executable, and FAILS now
  (no skill yet). [AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6]

## Wave 3 — Skill and runner (green)

- [ ] T4: Add `plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh`
  — thin wrapper delegating to `scripts/spawn-fresh-session.sh`, positional
  `<spec-dir> [project-dir]`, `--base` (default `git merge-base main HEAD`),
  `--dry-run`, `--print-harness`, `--skip-permissions`; report path
  `.foundry/reports/code-review/<timestamp>-code-review.md`; read-only prompt
  (dep T3). Gate: `spawn-code-reviewer.sh --print-harness` with
  `AGENT_HARNESS=codex` prints `codex` and exits without spawning (no report
  written, no session launched); a `--dry-run` launch carries the spec
  dir, the diff range, and the report path; a `--dry-run` without `--base` shows
  the `git merge-base main HEAD` default range and `--dry-run --base <ref>`
  overrides it. [AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6]
- [ ] T5: Add `plugins/foundry/skills/code-review/SKILL.md` — frontmatter
  `name: code-review`, `Use when` description, provenance header (industry code
  review + `spec-review` sibling, no glossary entry), the dimension table, the
  output contract (`CODE_REVIEW: PASS|FAIL` + `FLAGGED:` footer; severity,
  dimension, `file:line`, evidence, problem, fix), fresh-context workflow, and
  the contract reads (dep T4). Gate: `tests/code_review_skill_test.sh` PASS.
  [AC-1.1, AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-2.5]

## Wave 4 — Dimension grading contract

- [ ] T6: Encode the evidence-not-claims dimensions in `SKILL.md` — lifecycle
  evidence (read spec/diff/board/`validation.md`), complete implementation
  (AC → Scenario → test → code matrix; mechanical artifacts, not keyword
  mapping), docs sync (RUN `python3 scripts/knowledge.py check`; verify each
  `design.md` architecture/class diagram matches the shipped components/classes
  and flag a drifted diagram), domain language (glossary terms;
  debt-term-in-`Replaces` is not a violation) (dep T5). Gate:
  `tests/code_review_skill_test.sh` PASS; the SKILL names each evidence source.
  [AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-4.1, AC-4.2]
- [ ] T7: Encode logging consistency, simplicity, clean interfaces, modular
  structure, performance/efficiency, sensible defaults, and robust tests in `SKILL.md` — production code
  must not mix raw `print`/`console.log`/`echo` with the Wide event for one unit
  of work (`print --help` is legitimate); size tripwires advisory (new >400,
  touched >800, +250 growth, function >80; exclude generated/vendor/tests);
  sensible documented defaults, no footgun/magic values; tests must discriminate,
  exercise the real path, and cover failure/edge cases (dep T6). Gate:
  `tests/code_review_skill_test.sh` PASS; the SKILL marks size tripwires advisory
  and names the robust-tests checks. [AC-4.3, AC-4.4, AC-5.1, AC-5.2, AC-5.3,
  AC-5.4, AC-5.5, AC-6.1, AC-6.2, AC-6.3]

## Wave 5 — Lifecycle placement

- [ ] T8: Update `plugins/foundry/skills/code/SKILL.md` — add a numbered Review
  stage between Knowledge and Finish (Verify → Knowledge → Review → Finish). The
  stages are 0–6 today with `- [ ] 6 Finish` last and matching body headers
  (`## 5 · Knowledge`, `## 6 · Finish`); renumber the checklist line to
  `- [ ] 7 Finish`, add a new `- [ ] 6 Review` line before it, add a
  `## 6 · Review` body section after `## 5 · Knowledge`, renumber the
  `## 6 · Finish` header to `## 7 · Finish`, and change the Frame path
  "All stages 1 → 6" to "1 → 7". Gate: no commit/PR with an unresolved
  blocking finding; size tripwires advisory; a docs/knowledge finding loops back
  to Knowledge (dep T5); blocking findings persisting after three rounds stop and
  escalate to the maintainer rather than looping. Gate:
  `tests/code_review_skill_test.sh` PASS (the delegation assertion); `code/SKILL.md`
  shows `- [ ] 6 Review` before `- [ ] 7 Finish`, a `## 6 · Review` section before
  `## 7 · Finish`, the Review gate prohibition, and the three-round escalation
  backstop (v1 — superseded by T22's 20-round ceiling; verify T8 against the v1
  commit, not the post-T22 state). [AC-7.1, AC-7.2, AC-7.3, AC-7.4, AC-7.5]

## Wave 6 — Discrimination fixture and eval

- [ ] T9: Add `evals/fixtures/code-review/` — a seeded tree plus
  `answer-key.json` in the reviewer fixture's shape, seeding exactly five defects:
  an unimplemented AC, a production path mixing a Wide event with a raw `print(`,
  an oversized file/function, a public CLI/API behavior added without docs, and a
  debt term used in changed text outside a glossary `Replaces` column; plus
  decoys: a legitimate `print --help`, a large generated fixture, and a debt term
  used only in a glossary `Replaces` column. Gate: `score_review.py` parses
  `answer-key.json`, lists exactly five violations, and reports the seeded
  violation and decoy signatures. [AC-8.3, AC-8.4]
- [ ] T10: Add `evals/harness/code-review-eval.sh` — run a headless review over
  the fixture, score findings only via `score_review.py` (unchanged), reference
  `plugins/foundry/skills/code-review/SKILL.md`, never the removed agent file
  (deps T5, T9). Gate: a score-only run over a clean findings file passes
  (mean recall over the five seeded defects ≥ 4/5, zero decoy hits); a findings
  file missing two or more seeded signatures drops mean recall below 4/5 and
  fails; flagging a decoy fails. [AC-8.1, AC-8.2, AC-8.5]

## Wave 7 — Cross-model refuter

- [ ] T11: Add the cross-model refuter spawn to
  `plugins/foundry/skills/code-review/scripts/spawn-code-reviewer.sh` — after the
  reviewer emits its candidate `FLAGGED:` footer, detect the reviewer's harness
  family via the shared runner, pin the complementary family with `AGENT_HARNESS`,
  and spawn a fresh-context refuter read-only with ONLY the candidate findings and
  the diff or artifact (not the report prose); rewrite the final footer to the
  candidate set minus the refuter's DROPs and recompute the verdict; skip the pass
  and run single-agent when only one harness family is available (dep T4). Gate:
  `tests/code_review_skill_test.sh` PASS; a `--dry-run` shows the refuter spawn on
  the complementary family with the read-only, candidate-findings-only prompt; a
  `--dry-run` with one harness family available shows the refuter skipped and the
  reviewer single-agent. [AC-9.1, AC-9.2, AC-9.5, AC-9.6]
- [ ] T12: Encode the refuter contract in
  `plugins/foundry/skills/code-review/SKILL.md` — a single asymmetric refute pass
  (not a debate or multi-round argument): per candidate finding, KEEP only with
  concrete evidence the finding is real else DROP; the refuter may only REMOVE a
  `FLAGGED:` finding, never ADD one (recall-monotone-down, precision-up); context
  isolation — the refuter sees only the candidate findings and the diff/artifact,
  never the reviewer's reasoning (dep T11). Gate: `tests/code_review_skill_test.sh`
  PASS; the SKILL marks the refuter DROP-only, asymmetric (not debate), and
  context-isolated. [AC-9.3, AC-9.4, AC-9.7]
- [ ] T13: Add the reviewer-alone vs reviewer+refuter A/B to
  `evals/harness/code-review-eval.sh` — score both arms with `score_review.py`
  unchanged against the same `answer-key.json`, and enable the refuter by default
  ONLY if the reviewer+refuter arm holds mean recall ≥ 4/5 AND decoy hits = 0,
  else disable it and run single-agent (deps T10, T11). Gate: a score-only A/B
  where the refuter arm holds recall ≥ 4/5 and zero decoy hits enables the
  refuter; a refuter arm that drops a real violation below 4/5 disables it,
  proving the eval gates enablement by discrimination. [AC-9.8]

## Wave 8 — Validation, knowledge, finish

- [ ] T14: Register the review eval in `knowledge/validation.md` (L3, manual,
  required green for a version bump) and confirm the static skill test runs inside
  `scripts/check-fast.sh` while the review eval does not (deps T3, T13). Gate:
  `scripts/check-fast.sh` runs `tests/code_review_skill_test.sh` and does not run
  the review eval; `knowledge/validation.md` lists the L3 row. [AC-10.1, AC-10.2,
  AC-10.4]
- [ ] T15: Run `python3 scripts/knowledge.py check` and regenerate
  `knowledge/index.md`; log the change in `knowledge/log.md` (no glossary entry).
  Gate: knowledge check clean and index current. [AC-10.2]
- [ ] T16: Re-run `spec-review` on requirements, design, and tasks after any
  implementation-driven spec changes; apply findings. Gate: review report has no
  findings, or every finding has a recorded disposition and fix. [Spec README]
- [ ] T17: Run the canonical gate. Gate: `scripts/check-fast.sh` prints
  `check-fast: PASS`. Then move the card Validating → Done with the recorded
  PASS. [AC-10.2]

## Wave 8b — Tracer bullets (build + validate the risky primitives before composing them)

Each bullet builds a KEPT, tested primitive (not a throwaway) that a build-wave task
then composes — the Pragmatic-Programmer sense of a tracer bullet.

- [ ] T30: Build `wait-for-report.sh` — the synchronous-wait primitive: block until the
  report file ends with a `CODE_REVIEW:` verdict line (the runner spawns detached, so
  wait on the artifact, not the process), timing out nonzero so a hung or never-spawned
  reviewer fails (never a false PASS). Add `tests/wait_for_report_test.sh`; T19 composes
  it. Gate: a ready report succeeds, a late report blocks-then-reads, a verdict-less or
  absent report times out. [de-risks + builds for AC-11.1, AC-11.5]
- [ ] T31: Build `footer-algebra.sh` — the footer finding-set module: union + dedup +
  difference, keyed on ONE normalized signature; `recompute-footer.sh` delegates to its
  difference; T21 wires its union into the inner loop. Add
  `tests/code_review_footer_algebra_test.sh`. Gate: union dedups case/whitespace
  variants, keeps `AC-2.1` ≠ `AC-2.10`, difference drops by normalized key.
  [de-risks + builds for AC-12.2, AC-12.5]
- [ ] T32: Build `refuter-family.sh` — the cross-model family selector: pick a manifest
  family ≠ the reviewer's (`claude-code`→`claude`), else `none` for a single-family
  repo; T23 wires it into the runner (replacing the `AGENT_HARNESS` pin). Add
  `tests/code_review_refuter_family_test.sh`, which also asserts the refuter payload is
  the footer-algebra union (FLAGGED-only, no prose/verdict). Gate: claude↔codex
  selection, single-family→none, footer-only payload. [de-risks + builds for AC-9.5, AC-13.1]

## Wave 9 — Synchronous runner foundation (revision; fixes CR-1, CR-2, CR-17)

- [ ] T18: Add `tests/code_review_cycle_test.sh` (red) — deterministic loop-control
  test mirroring `tests/spec_convergence_hook_test.sh`: stub the reviewer via the
  test-only reviewer-command seam and feed scripted `CODE_REVIEW:`/`FLAGGED:`
  sequences. Assert `code-review-convergence-hook.sh` returns continue-on-FAIL (exit
  2), converged-on-PASS (exit 0), escalate at the 20-round ceiling (exit 4), rejects
  a missing verdict line, fails (never converges) on a failed/timed-out review, and
  that the runner unions findings and recomputes the verdict after a refuter DROP.
  Gate: the test exists, is executable, and FAILS now (no hook / synchronous runner
  yet). [AC-7.5, AC-7.6, AC-11.1, AC-11.2, AC-11.3, AC-11.4, AC-11.5]
- [ ] T19: Make `spawn-code-reviewer.sh` synchronous — block until the reviewer's
  report is written via `wait-for-report.sh` (built in T30), exiting nonzero with no verdict
  if it times out (never PASS); extract the `FLAGGED:` footer, and compute the
  verdict from the surviving blocking findings (never a scraped free-text line);
  after the refuter, rewrite the footer to candidates-minus-DROPs and recompute;
  pass the refuter ONLY the extracted footer + diff (deps T18, T30). Gate: the
  cycle-control test's synchronous/verdict/refuter-recompute/timeout arms PASS.
  [AC-11.1, AC-11.2, AC-11.3, AC-11.4, AC-11.5]

## Wave 10 — Inner review-convergence loop (revision)

- [ ] T20: Add `plugins/foundry/skills/code-review/references/convergence.md` — the
  inner/outer loop mechanics (union, 2-consecutive-no-new, 20-pass and 20-round
  caps, refuter-once-on-union) — point `SKILL.md` to it, and add it to the static
  test's skill-text concat (dep T5). Gate: `tests/code_review_skill_test.sh` PASS;
  `SKILL.md` links `references/convergence.md`. [AC-12.1, AC-12.2, AC-12.3]
- [ ] T21: Implement the inner loop in the runner — re-review in fresh context, union
  findings via the **footer-algebra** `union` (`footer-algebra.sh`, built in T31; one
  normalized key so `AC-2.1` ≠ `AC-2.10`), stop at two consecutive no-new passes or a
  20-pass ceiling, run the refuter once over the union; hoist immutable inputs
  (docs-sync, glossary, size pre-scan) once per loop; the inner loop is the default,
  `--single-pass` skips it (deps T19, T31). Gate: the cycle-control test's inner-loop +
  union arms PASS; the footer-algebra unit test exercises union/difference on `AC-2.1`
  vs `AC-2.10`. [AC-12.1, AC-12.2, AC-12.3, AC-12.4, AC-12.5]

## Wave 11 — Outer fix-convergence loop (revision; supersedes T8's cap)

- [ ] T22: Add `plugins/foundry/scripts/code-review-convergence-hook.sh` (the OUTER
  fix loop, mirroring `spec-convergence-hook.sh`: run one converged review via the
  wrapper, return continue/converged/escalate, count rounds, 20-round ceiling) and
  wire `code/SKILL.md` Stage 6 to it — fix via the SDLC between rounds, stop on PASS;
  hold Stage 6 within the 120-line budget by deferring detail to
  `references/convergence.md` (deps T19, T20). Gate: `tests/code_review_cycle_test.sh`
  outer-loop arms PASS; `tests/code_review_skill_test.sh` PASS;
  `scripts/check-context-budget.sh` PASS; `code/SKILL.md` shows the 20-round ceiling
  and the SDLC fix path. [AC-7.4, AC-7.5, AC-7.6]

## Wave 12 — Configuration A (revision; CR-5/6/7/19)

- [ ] T23: Config-A in the runner — derive refuter families from the manifest
  `harnesses` via `refuter-family.sh` (built in T32); add `--harness` (replacing the
  `AGENT_HARNESS` production pin); single-sourced named-constant cap defaults with
  `--review-cap`/`--fix-cap`/`--consecutive-clean` overrides; `--base` via the
  shared `resolve_base`; stop forwarding `--skip-permissions` to the read-only
  reviewer/refuter (deps T19, T32). Gate: `tests/code_review_skill_test.sh` PASS (with
  its diff-base assertion updated from `git merge-base main HEAD` to the
  `origin/HEAD → main → HEAD` resolver, and its `--skip-permissions` assertion flipped
  from 'bypass forwarded to the shared runner' to 'bypass NOT forwarded to the
  read-only reviewer/refuter', per AC-1.6); a `--dry-run` shows a manifest-derived refuter
  family selected via `--harness` and the resolved diff base; resolve all config once
  at the CLI into a config object threaded inward (no re-defaulting/env-reads in inner
  contexts). [AC-1.2, AC-1.6, AC-1.7, AC-9.5, AC-13.1, AC-13.2, AC-13.3, AC-13.4, AC-13.5]

## Wave 13 — Hardening, eval, traceability

- [ ] T24: Gitignore the runtime dirs — the bootstrap-generated `.gitignore` (and a
  verbatim seed if needed) MUST ignore `.foundry/reports/` and `.foundry/tmp/`, and
  the report path gains a `-<pid>` suffix to avoid same-second collision (CR-4).
  Gate: a bootstrap-eval assertion confirms a generated repo ignores both dirs.
- [ ] T25: Add `tests/code_review_eval_test.sh` (hermetic) — drive
  `code-review-eval.sh --score-ab` on two canned findings files: an Arm B holding
  recall ≥ 4/5 with zero decoys prints refuter ENABLED (exit 0); an Arm B dropping
  two real violations prints DISABLED (exit nonzero). Never spawns `claude` (CR-10).
  Gate: the test runs in `scripts/check-fast.sh` and passes. [AC-9.8]
- [ ] T26: Traceability — T7 now encodes the performance/efficiency dimension and
  traces AC-5.5; `design.md` carries a `## Metrics` section (CR-8). Gate: every AC
  in `requirements.md` maps to a task; `design.md` has a `## Metrics` section.

## Wave 14 — Verify the revision

- [ ] T27: Re-run `spec-review` to convergence on the revised
  `requirements`/`design`/`tasks`; apply findings. Gate: `SPEC_REVIEW: CLEAN`, or
  every finding has a recorded disposition. [Spec README]
- [ ] T28: `python3 scripts/knowledge.py check` clean; regenerate `index.md`; log
  the change in `knowledge/log.md`. Gate: knowledge check clean and index current.
- [ ] T29: Run the canonical gate and the cycle-control test; the L3 review eval
  green for the version bump. Gate: `scripts/check-fast.sh` prints `check-fast:
  PASS`; then move the card Validating → Done. [AC-10.2]

## Wave 15 — Agent calibration + spec grounding (precision: low false positives)

- [ ] T33: Extend `tests/code_review_skill_test.sh` (red) — assert the SKILL/dimensions
  text carries the calibration guardrails (cite `file:line` / evidence-or-drop; drop when
  unsure / zero-findings-is-fine; cluster; read context not the hunk; do-NOT-flag
  style/lint; severity by verifiability) and the spec-grounding rules (grade against the
  spec's ACs; never invent a requirement; a proposed fix is a hypothesis). Gate: the test
  exists, is executable, and FAILS now. [AC-14.1, AC-14.2, AC-14.3, AC-14.4, AC-14.5, AC-14.6, AC-14.7, AC-15.1, AC-15.2, AC-15.3, AC-15.4]
- [ ] T34: Encode the guardrails + spec-grounding in `SKILL.md` and
  `references/dimensions.md` — a Calibration block (evidence-or-drop, silence-beats-noise,
  cluster, read-context, no-style, severity-by-verifiability) and a Spec-grounding block;
  hold `SKILL.md` within the 120-line budget by keeping detail in `dimensions.md`
  (dep T33). Gate: `tests/code_review_skill_test.sh` PASS; `scripts/check-context-budget.sh`
  PASS. [AC-14.1, AC-14.2, AC-14.3, AC-14.4, AC-14.5, AC-14.6, AC-14.7, AC-15.1, AC-15.2, AC-15.3, AC-15.4]
- [ ] T35: Add **decoy** eval cases that punish false positives — seed in the fixture a
  style-only change, a spec-conforming behavior, an "omission" the spec does not require,
  and a plausible-but-unverifiable claim; the answer key marks each a decoy (dep T34).
  Gate: `score_review.py` fails a run that flags ANY decoy (MAX_DECOY_HITS = 0); a run
  that flags none passes. [AC-14.1, AC-14.3, AC-14.6, AC-15.1, AC-15.2]
- [ ] T36: Trace every new AC to a task; re-run `spec-review` to `SPEC_REVIEW: CLEAN`;
  `check-fast` green; move the card (deps T34, T35). Gate: all AC-14/AC-15 traced;
  spec-review CLEAN; `scripts/check-fast.sh` PASS. [AC-14.7, AC-15.3, AC-15.4]
