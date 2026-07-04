> **Status:** In progress (2026-07-03) — tracked on the [board](../../ROADMAP.md).

# foundry-cli-shim — requirements

The plugin ships skills only; `foundry` is a separate `uvx`-installed package with no PATH
entry. A session-agent (and a human) therefore cannot call a bare `foundry`, and the pin
lives in two places — `.foundry/config.toml` and a hardcoded `@tag` in the pre-push hook
and CI. A repo-local shim gives every caller one pin-free entry point.

## US-1 One entry point to the pinned CLI

As a caller in a bootstrapped repo (the `code` skill, CI, a human), I want a repo-local
command that runs the repo's pinned foundry, so I never type a version or a `uvx` line.

- AC-1.1 THE repo SHALL carry an executable `.foundry/bin/foundry` that forwards its
  arguments to the repo's foundry CLI.
- AC-1.2 WHEN `.foundry/bin/foundry` runs in a consumer repo, THE SYSTEM SHALL resolve the
  CLI from `[foundry] pin` and `repo_url` in `.foundry/config.toml` (the pinned `uvx` form).
- AC-1.3 WHEN `.foundry/bin/foundry` runs in foundry's own repo, THE SYSTEM SHALL run the
  local tree (`uv run --project`), never a pinned fetch — the self-host rule.
- AC-1.4 WHEN `.foundry/config.toml` lacks a pin or `repo_url` in a consumer repo, THE
  SYSTEM SHALL fail with a message naming the missing key.

## US-2 The pin lives in one place

As a maintainer, I want the hook and CI to route through the shim, so bumping the pin is a
one-line edit to `config.toml`.

- AC-2.1 WHEN a repo is bootstrapped, THE pre-push hook SHALL invoke `.foundry/bin/foundry
  gate` (no hardcoded tag), and `.foundry/config.toml` SHALL carry the pin.
- AC-2.2 WHEN the cli-shim migration runs on a convention-5 repo, THE SYSTEM SHALL install
  the shim and rewrite the pre-push hook and CI gate lines from the hardcoded pinned form
  to `.foundry/bin/foundry gate`, leaving the pin only in `config.toml`.

## US-3 Shipped as a convention break with a migration

- AC-3.1 THE change SHALL ship as convention 6: an `m006` migration module, a registry-head
  row, and a `conventionVersion` bump, installing the shim and collapsing the pin in
  existing repos.
- AC-3.2 THE migration detector SHALL key on a structural signal it removes (the shim
  absent while the hook hardcodes a pin), so a migrated repo never re-triggers.
- AC-3.3 Foundry's own repo SHALL carry a byte-identical shim copy (self-host gate) and its
  manifest `conventionVersion` SHALL equal the registry head.
