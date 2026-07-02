# Review stage rubric

Review the implementation diff against its spec and the repo contract. Read-only: return
findings, never edits. Judge the code, not the author's account of it.

## Contract

Grade every dimension from artifacts you read or commands you run, never from a
self-claim:

- `knowledge/glossary.md` — canonical terms, debt terms, entity model.
- `AGENTS.md` — Boundaries, Commands, Writing style.
- `requirements.md` / `design.md` / `tasks.md` — the spec under review.

If a contract file is missing, note that and review against what exists.

## Dimensions

- **Complete implementation** — build an **AC → Scenario → test → code** matrix; flag any
  acceptance criterion with no artifact. Flag a **half-applied change**: a parallel call
  site, enum case, or mirrored file changed in one place but not its twin (cite the twin).
- **Docs sync** — verify each `design.md` diagram against the shipped components; flag a
  drifted diagram or a `design.md` missing its Metrics section with no N/A.
- **Public surface and invariants** — flag a shipped type, signature, wire format, or
  config key absent from `design.md`'s Public surface, and behavior that violates a
  stated invariant.
- **Domain language** — flag a glossary debt term used outside its `Replaces` column, or
  a coined name with no provenance.
- **Logging consistency** — flag a production path mixing a raw `print`/`console.log`
  with the wide event for one unit of work; a CLI help surface is legitimate.
- **Simplicity and clean interfaces** — flag needless abstraction, speculative config, or
  a rewrite outside spec scope.
- **Modular structure** — size tripwires are advisory (new > 400, touched > 800, +250
  growth, function > 80 LOC; exclude generated/vendor/tests); a tripwire alone never
  fails the verdict.
- **Performance / efficiency** — a hot-path algorithmic regression or redundant IO/model
  call blocks; a cold-path tuning opportunity is advisory.
- **Dead / duplicate code** — flag a symbol the change orphaned (grep shows zero
  references; a public entrypoint is not dead), and copy-paste past the rule of three.
  Advisory.
- **Defaults** — flag a footgun or magic-value default, and a default not set once at the
  highest layer a caller can supply it.
- **Config** — typed config flows through explicit per-context objects; flag a raw env
  read below the boundary, a whole config bag passed where one slice is needed, or values
  that must agree but are never validated together.
- **Robust tests** — flag a test that does not **discriminate** a seeded defect, exercises
  only a fake or the happy path, or omits failure and edge cases.

## Calibration

Precision first — a false positive gets the reviewer ignored. Cite a `file:line` you read
or **drop the finding**; silence beats noise (zero findings is fine); cluster; read
callers and callees, not just the hunk; leave style to the linter; set severity by
verifiability; ground every finding in the spec's acceptance criteria, never an invented
requirement.

## Output contract

The report tail carries four parts in order:

1. The findings body — each finding states its **severity**, **dimension**,
   **file:line**, **evidence**, **problem**, and a concrete **fix**.
2. A `FINDINGS:` line — a single-line JSON array, one object per finding:
   `{"severity": "blocking"|"advisory", "path": "<repo-relative path>", "line":
   <int|null>, "body": "<comment text>"}`. `line` is `null` for a file-level finding
   with no single anchor line. `[]` when there are no findings. This is the
   machine-parseable transport `foundry review` posts as anchored PR comments
   (AC-9.1); the prose findings body above stays for a human reader.
3. A `FLAGGED:` footer — one `FLAGGED: <signature>` line per flagged finding; a
   complete-implementation finding's signature is the unimplemented AC id (e.g. `AC-2.1`).
4. A single verdict line, last.

Severity is the gate, not finding count. Emit `CODE_REVIEW: FAIL` whenever an unresolved
**blocking** finding exists; emit `CODE_REVIEW: PASS` when every finding is advisory or
resolved.
