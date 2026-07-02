# Plan stage rubric

Break the approved design into bite-sized TDD tasks in
`roadmap/specs/<feature>/tasks.md`.

## Intent

A plan a builder follows step by step with no design decisions left open. Each task is
small enough to land in one red→green cycle, names its exact paths and real code, and
respects the dependencies the design implies.

## Invariants

- Tasks are grouped in waves; tasks within a wave are independent and can land in
  parallel; each wave builds on the last.
- Every task is TDD: it names the test that lands red first and the code that turns it
  green.
- Every task names the gate that proves it done.
- A task names exact file paths, not vague intentions.
- Performance-sensitive work states its baseline before the task that changes the hot
  path, so the change is measured against it.

## Output contract

The plan gate is file-shaped, not a marker: it passes when `tasks.md` exists and is
approved per the run's autonomy level. This rubric states what a good plan holds; the
driver evaluates the gate.
