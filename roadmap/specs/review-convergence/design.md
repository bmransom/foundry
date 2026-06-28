> **Status:** Planned (2026-06-27) — design pending approval; tracked on the [board](../../ROADMAP.md).
> Companion: [requirements.md](requirements.md), [tasks.md](tasks.md).

# Design — review-convergence

## Decisions

- **Adopt code-review's severity gating, not a new scheme.** `code-review` already classes
  findings `blocking`/`advisory` and fails its verdict only on a surviving blocking finding
  ("severity is the gate, not finding count"). spec-review adopts that severity model and
  carries the `blocking` findings in its `FLAGGED:` footer (the convergence loop and
  `score_review.py` read the footer). This reuses code-review's vocabulary rather than
  inventing a second one; it does not change code-review.
- **`CLEAN` = no blocking, not no findings.** A binary gate over taste-level prose cannot
  converge (judges disagree on nits indefinitely). Gating on `blocking` lets advisory nits
  persist without blocking the Design gate — the Conventional-Comments / Google-`Nit:` model.
- **Blind by construction — for both review skills.** The convergence hooks already re-spawn
  a fresh reviewer each round; the failure was a *human* priming the re-review with a change
  summary. **`code-review` shares this gap** — its re-review is blind only by the runner, not
  by contract, and its refuter is DROP-only (it removes false positives, never recovers a
  missed finding). Both `spec-review` and `code-review` are amended to forbid priming — the
  reviewer gets artifact + contract only, and no primed inline pass substitutes for it. (A
  judge told what changed exhibits self-enhancement bias; the COE records the live instance.)
- **Objective prose → a linter; subjective prose → advisory.** Deterministic writing-style
  rules belong in a gate lint (reproducible, no asymptote); taste belongs to the judge as
  advisory. Grounded in the documented "a too-subjective rule cannot be enforced" lesson.
- **No new caps.** The existing per-spec round counter and escalation stay; only the *stop
  condition* changes from "zero findings" to "no unresolved blocking" — which the stateless
  blind reviewer can emit directly (it re-reads the whole artifact each round; "new vs. old"
  would need state it does not have).
- **One cross-family pass, two combine-rules.** The cross-family pass already in
  `spawn-code-reviewer.sh` (spawn a context-isolated session on the complementary harness via
  the shared `spawn-fresh-session.sh` + `refuter-family.sh`) is extracted to a shared helper
  parameterized by goal prompt + combine-rule. code-review keeps **DROP-only** (its risk is
  over-flagging); spec-review uses **UNION** (its risk is missing). The combine-rules are
  opposite because the failure modes are: precision-up for a diff, recall-up for a spec. Each
  one-directional rule keeps its monotonicity guarantee. Like code-review's refuter, the
  spec-review pass ships enabled only after an A/B eval proves recall-up with no decoy
  regression.

## Mechanism

```mermaid
flowchart LR
  review[spec-review: label each finding] --> sev{blocking?}
  sev -->|yes| footer[FLAGGED: blocking only]
  sev -->|no| adv[advisory — not gated]
  footer --> verdict{any blocking?}
  verdict -->|no| clean[SPEC_REVIEW: CLEAN → converged]
  verdict -->|yes| findings[SPEC_REVIEW: FINDINGS → blind re-pass]
  findings --> review
  prose[objective writing-style rules] --> lint[deterministic linter in the gate]
```

| Surface | Change |
|---|---|
| `plugins/foundry/skills/spec-review/SKILL.md` | Output contract: each finding carries `blocking`/`advisory`; `FLAGGED:` lists blocking only; `CLEAN` = no unresolved blocking. The "Flag" section classes contract violations as blocking, taste as advisory. Fresh-context workflow: the re-pass is blind — **never** hand the reviewer a change summary. |
| `plugins/foundry/skills/code-review/SKILL.md` | Fresh-context workflow: the re-pass is blind — never hand the reviewer a change summary; replace the "review inline and say so" escape hatch with "hold the gate" when fresh context is unavailable (no primed inline pass). Severity gating is already present — unchanged (US-2 only). |
| `plugins/foundry/scripts/spec-convergence-hook.sh` | Verdict semantics now "CLEAN = no blocking"; the stop token is unchanged (it already reads the verdict line). Reword the human-facing CLEAN message from "house-style clean" to "no blocking findings remain" (advisory prose may persist); confirm the hook still converges and escalates correctly. |
| `scripts/prose-lint.py` (+ test, verbatim twins) | New deterministic linter: a defined needless-word set (generic English hedges/qualifiers, no repo vocabulary) + debt terms **derived at runtime from the consumer's `knowledge/glossary.md`** "Replaces (now debt)" column (only the mechanism ships in the twin — never a term list, per mechanisms-not-content); wired into `check-fast.sh`. |
| `evals/harness/spec-convergence-eval.sh` + `evals/fixtures/spec-convergence` | **Migrate the existing seeded hedge defect** (`SEEDED-DEFECT-HEDGE` / `SPEC_CONVERGENCE_SIGNATURE`): under the new rule a prose hedge is advisory, so a correct loop would emit `CLEAN` with it present and trip the eval's fake-clean branch. Re-cast it as a **blocking** contract violation (so `CLEAN` still requires its removal). Then add the blocking-holds / nit-converges / primed-vs-blind discrimination cases — the oracle must branch on severity: a **blocking** signature must be gone before `CLEAN`, an **advisory** signature may remain (the inverse of the current grep-presence-means-fail logic). |
| `knowledge/log.md` | Log the convergence change. **No `glossary.md` row** — `blocking`/`advisory` are generic industry terms with prior art (Conventional Comments / Google `Nit:`), so they earn no canonical row; this matches code-review's own no-row choice and the "no new canonical name" claim. |
| `evals/fixtures/reviewer/answer-key.json` + `reviewer-eval` | **Changes** — the recall set seeds prose violations (V7 passive/buried-point, V8 needless-qualifier, V9 prose-should-be-table) that the new contract demotes to **advisory**, so they leave the blocking-only footer and `score_review.py` would score them as misses (recall ~0.97 → ~0.7, i.e. 7 of 10 scored). Reassign only **V8** (needless-qualifier) to `prose-lint`'s discrimination set — a lintable objective rule. **V7** (passive/buried-point) and **V9** (prose-should-be-table) are *subjective* judge calls the linter cannot make (passive detection is deferred, Out of scope), so demote them to **advisory** judge output and drop them from the scored recall set — they have no deterministic home, and that is the point. reviewer-eval recall then measures **blocking contract-violations only**. `score_review.py` itself is unchanged; `spec-convergence-eval.sh` uses an independent grep oracle. |
| `plugins/foundry/scripts/cross-family-review.sh` (extracted) + `spawn-code-reviewer.sh` | Extract the cross-family pass from `spawn-code-reviewer.sh` into a shared helper: given the complementary family (`refuter-family.sh`), a goal prompt, and a combine-rule, spawn the context-isolated pass via `spawn-fresh-session.sh`. `spawn-code-reviewer.sh` calls it with the **DROP** rule (behavior unchanged — proven by its existing footer-algebra tests). |
| `plugins/foundry/skills/spec-review/scripts/spawn-spec-reviewer.sh` + `spec-review/SKILL.md` | Wire the shared helper with the **UNION** rule + a spec-review goal prompt (independent second-family review of the artifact + contract; emit its own `blocking` findings). The footer becomes the reviewer's `blocking` set ∪ the second family's; the verdict re-derives. Document the pass in `SKILL.md` (a sibling to code-review's refuter section). Single-family repo → skip (AC-5.2). |
| `evals/harness/spec-convergence-eval.sh` (cross-family A/B) | A/B case: a fixture where the reviewer's family misses a `blocking` finding the complementary family catches; the UNION pass must recover it (recall-up) with no decoy-hit regression — the enablement gate (AC-5.6), mirroring code-review's refuter A/B. |

## Metrics

Discrimination, not green-ness: the eval seeds a **blocking** contradiction (the loop must
emit `FINDINGS` and hold the gate), a pure **prose nit** (the loop must reach `CLEAN` with the
nit demoted to advisory), and a **primed-vs-blind** case (a re-pass given a change summary
misses a seeded contradiction the blind pass catches). The **cross-family A/B**: on a fixture
where the reviewer's family misses a `blocking` finding the complementary family catches, the
UNION pass recovers it (recall-up) with no decoy-hit regression — the AC-5.6 enablement gate,
mirroring code-review's refuter A/B. `prose-lint.py` has its own discrimination test: a seeded
banned phrase exits non-zero, clean prose passes. Runtime: lint and hook are one-shot parses —
perf N/A.

## Out of scope

- A full Vale rollout — `prose-lint.py` starts with the rules the repo already states
  (glossary-derived debt terms, a small needless-word set), extensible later.
- Passive-voice detection — unreliable to lint deterministically (false positives); deferred,
  so the linter starts with debt terms + a needless-word set.
- A *DROP-only* refuter for spec-review — US-5's UNION cross-family pass supersedes it
  (spec-review's failure mode is misses, not false positives).
- Re-running spec-review across already-merged specs (a separate board/debt sweep).
