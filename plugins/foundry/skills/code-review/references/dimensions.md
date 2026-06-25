# Code-review dimensions

Grade every dimension from artifacts you read or commands you run — never from
the author's claims. A green claim is not evidence; the gate decides.

## The dimensions

| Dimension | Check | Evidence / how |
|---|---|---|
| **Lifecycle evidence** | spec exists; Scenario-before-code where knowable; a recorded gate PASS; Knowledge logged; board card state | Read `requirements.md`/`design.md`/`tasks.md`, the diff, `roadmap/ROADMAP.md`, `knowledge/validation.md`. Never treat an author's claim of a passing gate as evidence. |
| **Complete implementation** | every EARS AC and relevant task has code + a `features/` Scenario + a test | Build an **AC → Scenario → test → code** matrix from `requirements.md`/`tasks.md`. The Scenario+test mapping is the mechanical signal. Flag any AC with no implementing artifact. Keyword-mapping an AC to changed code alone is not coverage. |
| **Docs sync** | public behavior, commands, APIs, and concepts match code; no stale `index.md`; architecture/class diagrams in `design.md` match the shipped components/classes; `design.md` names metrics or an explicit N/A | **Run** `python3 scripts/knowledge.py check` yourself rather than trusting the report; if it fails, report a docs-sync finding. Diff README/knowledge/AGENTS against the change. Compare each `design.md` architecture or class diagram against the shipped components/classes and flag a diagram that has drifted from the code. Flag a `design.md` with no Metrics section and no N/A — the spec format requires one. |
| **Domain language** | glossary terms used; no debt terms; new canonical names cite provenance | Read `knowledge/glossary.md`. Flag changed text that uses a term in the `Replaces (now debt)` column OUTSIDE that column, or coins a canonical name without provenance. A debt term INSIDE a glossary `Replaces` cell is documentation, not a violation. |
| **Logging consistency** | production paths do not mix a raw `print`/`console.log`/`echo` with the **Wide event** for one unit of work | Grep the diff for raw output beside the structured event. A legitimate CLI surface such as `print --help` is not a violation — do not flag it. |
| **Simplicity** | no needless abstraction, speculative config, pattern cosplay, or rewrite outside spec scope | Judgment, grounded in the `design-patterns` skill. |
| **Clean interfaces** | small public surfaces; IO/vendor/filesystem at the edges; callers do not depend on internals | Judgment, grounded in `design-patterns` and `modular-structure`. AC-5.4: a needless abstraction or out-of-scope rewrite may be flagged under simplicity OR clean interfaces — reviewer judgment, not scored. |
| **Modular structure** | layout respected; no dumping grounds; no new top-level dir for one file; oversized files/functions | Mechanical LOC/function pre-scan over the diff plus judgment. |
| **Performance / efficiency** | hot-path algorithmic cost; redundant IO, model, or tool calls; unbounded allocation; per-item work that could be hoisted | Judgment, grounded in the `performance` skill. A clear hot-path regression is **blocking**; a cold-path tuning opportunity is **advisory**. |
| **Sensible defaults** | defaultable params have sensible documented defaults; no footgun defaults or unexplained magic values | Read changed signatures and config; flag a default that surprises or a magic value with no rationale. |
| **Robust tests** | tests **discriminate** — a seeded defect makes them fail; they exercise the real path, not just fakes or the happy path; they cover failure and edge cases | Read each test against the code it claims to cover. Flag a test that passes against a fake while the real path is untested, or one that omits timeouts, errors, and empty inputs. A test that cannot fail on a seeded defect asserts nothing. |

## Size tripwires (advisory)

Size tripwires are **advisory** review triggers, never a hard fail. A tripwire
alone never yields `CODE_REVIEW: FAIL`. Exclude generated, vendor, and test files
unless the test itself becomes unreadable:

- new source file > 400 LOC;
- touched source file > 800 LOC;
- + 250 LOC growth;
- function > 80 LOC.

## The cross-model refuter

After the reviewer emits its candidate `FLAGGED:` footer, a second fresh-context
**refuter** pass runs on a **different harness family** than the reviewer (e.g.
Codex when the reviewer is Claude), read-only.

- **Context isolation.** The refuter sees ONLY the candidate `FLAGGED:` findings
  and the diff or artifact — never the reviewer's reasoning or report prose, so it
  cannot be talked into agreement.
- **Per finding:** KEEP it only if you can produce concrete evidence the finding
  is real; else mark it DROP.
- **DROP-only.** The refuter may only REMOVE a `FLAGGED:` finding, never ADD one.
  The combined system is recall-monotone-down and precision-up.
- **Single asymmetric pass.** One pass, one direction — NOT a symmetric debate or
  a multi-round argument. A debate collapses to sycophantic consensus that can
  argue a real finding away.
- **Final footer** = the reviewer's candidate footer minus the refuter's DROPs;
  recompute `CODE_REVIEW` from the surviving blocking findings.
- **One family only?** Skip the refuter pass; the reviewer runs single-agent —
  graceful fallback, never a hard error.

The refuter ships enabled by default ONLY if the A/B eval
(`evals/harness/code-review-eval.sh`) holds **mean recall ≥ 4/5 AND decoy hits =
0** for the reviewer+refuter arm; otherwise it is disabled and the reviewer runs
single-agent. The eval is the gate.

## Calibration — precision is the reviewer's first duty

A false positive costs more than a missed nit: an over-flagging reviewer gets ignored.
Hold every finding to these before it ships:

- **Evidence or drop the finding.** Quote a `file:line` you actually read or grepped for
  every symbol, path, and range you cite; if you cannot point to it, drop the finding —
  never flag from memory or inference.
- **Silence beats noise.** Flag only what evidence shows is a real defect; when unsure,
  drop it. **Zero findings is a valid, good outcome** — never manufacture a finding to look
  thorough.
- **Cluster.** Report repeated instances of one pattern as a single finding, not many.
- **Read the context, not the hunk.** Check the definition, callers, and callees first; a
  diff-local claim the surrounding code contradicts is a false positive.
- **Leave style to the linter.** Never flag formatting, import order, or other lint-domain
  issues — the repo's deterministic tools own those, and an LLM is worse at them.
- **Severity by verifiability.** A mechanically verified correctness or security defect is
  blocking; a design-judgment or inferred-root-cause finding is advisory unless you can
  back it with evidence.

## Spec grounding — review against intent, never invent it

The consumer ran bootstrap, so the spec is present; use it as the statement of intent:

- Grade the diff against the spec's acceptance criteria. Behavior that conforms to the spec
  is not a defect, however you would have built it.
- Flag an omission only if a spec AC requires it. **Never invent a requirement** the spec
  does not state.
- Treat your own proposed fix as a **hypothesis** to verify against the spec and code, not
  proof the original is wrong.
- When the spec and the code disagree, flag the discrepancy; do not assume either side.
