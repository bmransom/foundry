#!/usr/bin/env bash
# foundry migration preflight — the deterministic clean-tree gate.
#
# Refuses a dirty working tree, then creates the migration branch. Branch creation
# rides on this gate: the migration cannot start on a dirty tree, because the only
# blessed way to make the branch is through this script. Prose asking the agent to
# "check cleanliness" proved skippable; this makes the refusal mechanical.
#
# Usage: preflight.sh <migration-id>   (e.g. okf-knowledge)
set -euo pipefail

id="${1:?usage: preflight.sh <migration-id>}"
root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "foundry-migrate: not inside a git repository" >&2; exit 1; }
cd "$root"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "foundry-migrate: REFUSED — the working tree is dirty." >&2
  echo "Commit or stash your changes, then re-run /foundry:update. A migration must" >&2
  echo "start from a clean baseline so it stays reviewable and revertible." >&2
  exit 1
fi

branch="foundry/migrate-$id"
git switch -c "$branch"
echo "foundry-migrate: clean tree — created and switched to $branch"
