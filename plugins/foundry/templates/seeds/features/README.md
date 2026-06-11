---
title: Feature files
description: Executable Gherkin — the single behavioral source of truth.
kind: reference
---

<!-- foundry-seed: features-readme v1 -->

# Feature files

Feature files are the executable spec: behavior is specified once, as Gherkin
Scenarios, and verified through the production entrypoints. The Scenario precedes
the code.

**New feature → add a Scenario. Enhancement → update it. Refactor → don't touch.**

## Two contract kinds

- **Outcome contracts** — shared Scenarios for the observable outcomes every
  entrypoint must produce. One feature file; every runner executes it.
- **Process contracts** — entrypoint-specific Scenarios for how one entrypoint
  behaves: its flags, errors, exit codes, exceptions.

## Runners

One runner per production entrypoint, each executing the shared Scenarios through
its own surface — the same contract, proven everywhere it ships. Internal detail
no entrypoint exposes stays in unit tests.
