# Build stage rubric

Implement the task plan in `tasks.md` — feature-file first, then TDD red→green.

## Intent

Working, tested behavior that satisfies the spec's acceptance criteria and no more. Every
new observable behavior earns its executable specification before its implementation, so
the test proves the behavior rather than trailing it.

## Invariants

- New observable behavior gets its Scenario in `features/` (per `features/README.md`)
  **before** its implementation; an after-the-fact test passes vacuously.
- Each step is TDD: the test lands red, then the code turns it green.
- The change stays surgical — it touches only what the task requires and removes only
  what the change orphaned.
- The implementation honors the repo's `AGENTS.md` Boundaries and the design's public
  surface and invariants.
- A test **discriminates**: it fails when the behavior is wrong, not only on the happy
  path or against a fake.

## Output contract

The build gate is command-shaped: it passes when the repo's test command
(`[gate].test`) exits 0. This rubric states what good implementation holds; the driver
runs the gate on exit status, with no marker to emit.
