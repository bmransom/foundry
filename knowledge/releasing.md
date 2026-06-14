---
title: Releasing
description: "How foundry cuts versioned releases: release-please, the eval gate, and overrides."
type: guide
---

# Releasing

[release-please](https://github.com/googleapis/release-please) automates versioning from
Conventional Commits. You never bump a version or write the changelog by hand.

## How a release happens

Each push to `main` opens or updates a **Release PR**. release-please reads the commits
and proposes the next version:

| Commit | Bump |
|---|---|
| `fix:` | patch |
| `feat:` | minor |
| `!` or `BREAKING CHANGE:` | major |
| `docs`, `chore`, `ci`, … | none |

Merging the Release PR bumps `plugins/foundry/.claude-plugin/plugin.json` — the version
users receive — along with the README badge and `CHANGELOG.md`, then tags `vX.Y.Z` and
cuts a GitHub Release.

## The gate (AC-2.3)

A version ships only on a green Layer-3 eval. `check-fast` and `bootstrap-eval` run on the
Release PR; branch protection on `main` requires both to merge.

## Overrides

- Force a version with a `Release-As: x.y.z` commit footer.
- Let release-please own `CHANGELOG.md` and the version fields; never edit them by hand.

## Setup

- Set `RELEASE_PLEASE_TOKEN` (a PAT) so the Release PR triggers CI; the action falls back
  to `GITHUB_TOKEN`, which cannot.
- Remove `bootstrap-sha` from `release-please-config.json` after the first Release PR.
