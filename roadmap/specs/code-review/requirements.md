> **Status:** Ready (2026-06-20) — tracked on the [board](../../ROADMAP.md).
> Companion: [design.md](design.md), [tasks.md](tasks.md).

# Requirements — code review

## User stories

### US-1: Review a diff in fresh context without editing it

As a Foundry user, I want a read-only code review of my change in fresh context
so a reviewer sees the code, not my rationale, and never mutates the worktree.

Acceptance criteria:

- AC-1.1 WHEN the user runs `spawn-code-reviewer.sh <spec-dir> [project-dir]`,
  THE SYSTEM SHALL launch a fresh-context review of the diff for that spec and
  SHALL NOT edit any file in the consumer repo.
- AC-1.2 WHEN no `--base` is given, THE SYSTEM SHALL set the diff base to
  `git merge-base main HEAD` (range `<base>..HEAD`); `--base <ref>` SHALL override
  the base.
- AC-1.3 WHEN the review runs, THE SYSTEM SHALL write the full report to
  `.foundry/reports/code-review/<timestamp>-code-review.md`.
- AC-1.4 WHEN `--print-harness` is given, THE SYSTEM SHALL print the detected
  harness and exit without spawning a review.
- AC-1.5 WHEN `--dry-run` is given, THE SYSTEM SHALL print the launch command
  naming the harness, the spec dir, the diff range, the fresh-session prompt path,
  and the report path, and SHALL NOT spawn a review.
- AC-1.6 WHEN `--skip-permissions` is given, THE SYSTEM SHALL pass the permission
  bypass to the shared fresh-session runner.

### US-2: Emit machine-readable findings for scoring

As a maintainer, I want the review to end with a deterministic verdict and a
machine-readable footer so an eval scores findings, not prose or transcript.

Acceptance criteria:

- AC-2.1 WHEN the review finishes, THE SYSTEM SHALL order the report tail as
  findings body, `FLAGGED:` footer, then a single final line `CODE_REVIEW: PASS`
  or `CODE_REVIEW: FAIL`.
- AC-2.2 WHEN the review finishes, THE SYSTEM SHALL place the `FLAGGED:` footer —
  one `FLAGGED: <flagged signature>` line per flagged finding — after the findings
  body and before the verdict line; for a complete-implementation finding the
  signature SHALL be the unimplemented AC id, e.g. `AC-<n>.<m>`.
- AC-2.3 WHEN the review reports a finding, THE SYSTEM SHALL state its severity,
  dimension, `file:line`, evidence, problem, and a concrete fix.
- AC-2.4 WHEN the review finds an unresolved blocking finding, THE SYSTEM SHALL
  emit `CODE_REVIEW: FAIL`.
- AC-2.5 WHEN every finding is advisory or resolved, THE SYSTEM SHALL emit
  `CODE_REVIEW: PASS`.

### US-3: Trust evidence, never self-claims

As a maintainer, I want every dimension graded from artifacts the reviewer reads
or runs, never from the author's assertions, so a green claim cannot manufacture
a pass.

Acceptance criteria:

- AC-3.1 WHEN grading lifecycle evidence, THE SYSTEM SHALL read the spec files,
  the diff, `roadmap/ROADMAP.md`, and `knowledge/validation.md`, and SHALL NOT
  treat an author's claim of a passing gate as evidence.
- AC-3.2 WHEN grading complete implementation, THE SYSTEM SHALL build an
  AC → Scenario → test → code coverage matrix from `requirements.md` and
  `tasks.md`, and SHALL flag any AC with no implementing artifact.
- AC-3.3 WHEN grading complete implementation, THE SYSTEM SHALL use mechanical
  artifacts as the coverage signal and SHALL NOT pass an AC by keyword-mapping it
  to changed code alone.
- AC-3.4 WHEN grading docs sync, THE SYSTEM SHALL run
  `python3 scripts/knowledge.py check` itself and SHALL NOT trust the report.
- AC-3.5 WHEN grading docs sync, THE SYSTEM SHALL verify that any architecture or
  class diagram in `design.md` matches the shipped components/classes and SHALL
  flag a diagram that has drifted from the code.

### US-4: Hold the repo language and logging contract

As a maintainer, I want the review to enforce the glossary and the structured
logging convention so domain language and one canonical log line per unit of
work stay intact.

Acceptance criteria:

- AC-4.1 WHEN grading domain language, THE SYSTEM SHALL read
  `knowledge/glossary.md` and flag changed text that uses a debt term or coins a
  canonical name without provenance.
- AC-4.2 WHEN a debt term appears only in the glossary's `Replaces (now debt)`
  column, THE SYSTEM SHALL NOT flag it.
- AC-4.3 WHEN production code mixes a raw `print`/`console.log`/`echo` with the
  structured Wide event for one unit of work, THE SYSTEM SHALL flag the raw
  output signature.
- AC-4.4 WHEN a raw print is a legitimate CLI surface such as `print --help`, THE
  SYSTEM SHALL NOT flag it.

### US-5: Flag oversized, footgun, and inefficient changes by judgment

As a maintainer, I want size, defaults, simplicity, and efficiency findings
surfaced with mechanical tripwires plus judgment, so size warnings inform rather
than block and performance tuning opportunities surface without false blocks.

Acceptance criteria:

- AC-5.1 WHEN a changed file or function crosses a size tripwire — new file
  >400 LOC, touched file >800 LOC, +250 LOC growth, function >80 LOC — THE SYSTEM
  SHALL flag it as advisory and SHALL NOT fail solely on a size tripwire.
- AC-5.2 WHEN computing size tripwires, THE SYSTEM SHALL exclude generated,
  vendor, and test files unless the test itself becomes unreadable.
- AC-5.3 WHEN a defaultable parameter lacks a sensible documented default or
  carries a footgun default or unexplained magic value, THE SYSTEM SHALL flag it.
- AC-5.4 WHEN the change adds a needless abstraction, speculative config, or a
  rewrite outside the spec scope, THE SYSTEM SHALL flag it under either the
  simplicity or the clean-interfaces dimension; the choice between those two
  dimensions is reviewer judgment and is not scored.
- AC-5.5 WHEN the change introduces an avoidable inefficiency — a hot-path
  algorithmic regression, redundant IO or model/tool calls, an unbounded
  allocation, or per-item work that could be hoisted — THE SYSTEM SHALL flag it
  under the performance dimension as a tuning opportunity, grounded in the
  `performance` skill; a clear hot-path regression SHALL be blocking and a
  cold-path opportunity SHALL be advisory.

### US-6: Require discriminating tests

As a maintainer, I want the review to flag tests that pass against fakes while
the real path is broken so the recurring "fakes-green, real-path-broken" failure
cannot ship.

Acceptance criteria:

- AC-6.1 WHEN grading tests, THE SYSTEM SHALL flag a test that does not
  discriminate — a seeded defect in the code under test would not make it fail.
- AC-6.2 WHEN grading tests, THE SYSTEM SHALL flag a test that exercises only a
  fake or the happy path and never the real path it claims to cover.
- AC-6.3 WHEN grading tests, THE SYSTEM SHALL flag missing coverage of failure
  and edge cases such as timeouts, errors, and empty inputs.

### US-7: Gate Finish on the review

As a Foundry maintainer, I want the code lifecycle to run review as a numbered
stage after Knowledge and before Finish so no commit or PR ships with an
unresolved blocking finding.

Acceptance criteria:

- AC-7.1 WHEN the code lifecycle runs, THE SYSTEM SHALL place a numbered Review
  stage after Knowledge and before Finish: Verify → Knowledge → Review → Finish.
- AC-7.2 WHEN the Review stage finds an unresolved blocking finding, THE SYSTEM
  SHALL prohibit Finish — no commit or PR — until it is fixed and re-reviewed.
- AC-7.3 WHEN the Review stage finds only advisory findings such as size
  tripwires, THE SYSTEM SHALL permit Finish.
- AC-7.4 WHEN a Review finding is a docs or knowledge gap, THE SYSTEM SHALL loop
  back to the Knowledge stage before re-review.
- AC-7.5 WHEN blocking findings persist after three Review rounds, THE SYSTEM
  SHALL stop and escalate to the maintainer rather than re-review indefinitely —
  persistent blocking findings signal a design problem, not a wording fix.

### US-8: Prove discrimination with a seeded fixture

As a Foundry maintainer, I want a seeded fixture and an eval that scores findings
only so the review is graded by what it catches, not by green-ness.

Acceptance criteria:

- AC-8.1 WHEN the eval scores a review, THE SYSTEM SHALL score the findings only
  and SHALL NOT score the transcript.
- AC-8.2 WHEN the eval scores a review, THE SYSTEM SHALL reuse
  `evals/harness/score_review.py` unchanged.
- AC-8.3 WHEN the fixture is seeded, THE SYSTEM SHALL seed exactly five defects:
  an unimplemented AC, a production path mixing a Wide event with a raw `print(`,
  an oversized file or function, a public CLI/API behavior added without docs, and
  a debt term used in changed text outside a glossary `Replaces` column.
- AC-8.4 WHEN the fixture is seeded, THE SYSTEM SHALL include decoys: a
  legitimate `print --help`, a large generated fixture, and a debt term used only
  in a glossary `Replaces` column; the decoy debt term SHALL differ from the
  seeded-defect debt term so the violation and the decoy carry distinct `FLAGGED:`
  signatures the substring scorer can separate — mirroring the reviewer fixture,
  where every violation and decoy has a unique signature.
- AC-8.5 WHEN the eval runs N runs against the seeded fixture, THE SYSTEM SHALL
  require mean recall over the five seeded defects ≥ 4/5 across the N runs and
  zero decoy hits — `score_review.py`'s `RECALL_BAR`, computed against the five
  seeded violations.

### US-9: Cut false positives with a cross-model refuter

As a maintainer, I want a second fresh-context refuter pass on a different
harness family to drop the reviewer's false positives so precision rises without
risking recall.

Acceptance criteria:

- AC-9.1 WHEN the reviewer has emitted its findings and `FLAGGED:` footer, THE
  SYSTEM SHALL run a second fresh-context refuter pass over the candidate findings
  before producing the final footer.
- AC-9.2 WHEN the refuter pass runs, THE SYSTEM SHALL give the refuter ONLY the
  candidate `FLAGGED:` findings and the diff or artifact under review, and SHALL
  NOT give it the reviewer's reasoning or report prose.
- AC-9.3 WHEN the refuter judges a candidate finding, THE SYSTEM SHALL require
  concrete evidence the finding is real to KEEP it and SHALL mark it DROP
  otherwise.
- AC-9.4 WHEN the refuter pass runs, THE SYSTEM SHALL only REMOVE a `FLAGGED:`
  finding and SHALL NOT add a `FLAGGED:` finding — the combined system is
  recall-monotone-down and precision-up.
- AC-9.5 WHEN a refuter runs, THE SYSTEM SHALL run it on a different harness
  family than the reviewer, read-only.
- AC-9.6 WHEN only one harness family is available, THE SYSTEM SHALL skip the
  refuter pass and run the reviewer single-agent.
- AC-9.7 WHEN the refuter pass runs, THE SYSTEM SHALL run a single asymmetric
  refute pass and SHALL NOT run a symmetric debate or multi-round argument.
- AC-9.8 WHEN the discrimination eval gates the refuter, THE SYSTEM SHALL run an
  A/B comparison over the seeded fixture — reviewer-alone vs reviewer+refuter —
  scored by `score_review.py` unchanged, and SHALL enable the refuter by default
  ONLY if reviewer+refuter holds mean recall ≥ 4/5 AND decoy hits = 0; otherwise
  THE SYSTEM SHALL disable the refuter and run the reviewer single-agent.

### US-10: Keep the first release narrow

As a Foundry maintainer, I want v1 to prove the skill before adding per-task
review, AST metrics, PR-comment posting, or auto-fix.

Acceptance criteria:

- AC-10.1 WHEN v1 runs, THE SYSTEM SHALL provide one required final review and
  SHALL NOT run per-task incremental review.
- AC-10.2 WHEN v1 runs, THE SYSTEM SHALL stay out of `scripts/check-fast.sh`; only
  the static skill test runs in the fast gate, and the review eval is L3, manual,
  required green for a version bump.
- AC-10.3 WHEN v1 documents future work, THE SYSTEM SHALL name per-task review,
  language-agnostic AST complexity metrics, PR-comment posting, and `--fix`
  auto-application as deferred.
- AC-10.4 WHEN v1 reviews, THE SYSTEM SHALL NOT depend on any non-Foundry review
  skill being installed.

## Out of scope

- A glossary entry for code review (generic prior art; provenance lives in the
  SKILL header, mirroring `spec-review`).
- A second scorer — the existing `score_review.py` is fixture-generic and scores
  both arms of the refuter A/B unchanged.
- A symmetric debate or multi-round argument between reviewer and refuter — the
  refuter is a single asymmetric DROP-only pass.
- A refuter that adds findings — it can only remove a reviewer's `FLAGGED:` line.
- Per-task incremental review.
- Language-agnostic AST complexity metrics.
- PR-comment posting and `--fix` auto-application.
- Running `code-review` inside `scripts/check-fast.sh`.
- Repointing `evals/harness/reviewer-eval.sh` off the removed
  `agents/spec-reviewer.md` — a separate card.
