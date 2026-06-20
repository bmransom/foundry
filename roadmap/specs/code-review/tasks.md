> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [design.md](design.md).

# Tasks — code review

Waves run top to bottom. Tasks within a wave are parallel unless they name a
dependency. Every task names the gate that proves it and the AC it satisfies.

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
  mapping), docs sync (RUN `python3 scripts/knowledge.py check`), domain language
  (glossary terms; debt-term-in-`Replaces` is not a violation) (dep T5). Gate:
  `tests/code_review_skill_test.sh` PASS; the SKILL names each evidence source.
  [AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-4.1, AC-4.2]
- [ ] T7: Encode logging consistency, simplicity, clean interfaces, modular
  structure, sensible defaults, and robust tests in `SKILL.md` — production code
  must not mix raw `print`/`console.log`/`echo` with the Wide event for one unit
  of work (`print --help` is legitimate); size tripwires advisory (new >400,
  touched >800, +250 growth, function >80; exclude generated/vendor/tests);
  sensible documented defaults, no footgun/magic values; tests must discriminate,
  exercise the real path, and cover failure/edge cases (dep T6). Gate:
  `tests/code_review_skill_test.sh` PASS; the SKILL marks size tripwires advisory
  and names the robust-tests checks. [AC-4.3, AC-4.4, AC-5.1, AC-5.2, AC-5.3,
  AC-5.4, AC-6.1, AC-6.2, AC-6.3]

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
  backstop. [AC-7.1, AC-7.2, AC-7.3, AC-7.4, AC-7.5]

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
