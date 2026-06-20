#!/usr/bin/env bash
# worktree-retire.sh --delete-branch: deletes a foundry/fs/* branch after
# removing the worktree, refuses an unmerged branch without --force, and deletes
# it with --force. Branch deletion runs only after worktree removal.
#
# Hermetic: needs only git.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RETIRE="$REPO/scripts/worktree-retire.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -x "$RETIRE" ] || fail "missing executable worktree-retire.sh"

scratch="$(mktemp -d)"
repo="$scratch/repo"
trap 'git -C "$repo" worktree prune 2>/dev/null || true; rm -rf "$scratch"' EXIT

git init -q -b main "$repo"
git -C "$repo" config user.email "foundry@example.test"
git -C "$repo" config user.name "Foundry Test"
printf '.foundry/tmp/\n' > "$repo/.gitignore"
printf '# fixture\n' > "$repo/README.md"
git -C "$repo" add .gitignore README.md
git -C "$repo" commit -qm "initial"
base="$(git -C "$repo" rev-parse HEAD)"

branch_exists() { git -C "$repo" rev-parse --verify -q "refs/heads/$1" >/dev/null 2>&1; }

# --- AC-5.1: --delete-branch deletes a MERGED foundry/fs/* branch (git -d).
merged_branch="foundry/fs/merged-demo"
merged_wt="$scratch/merged-wt"
git -C "$repo" worktree add -q -b "$merged_branch" "$merged_wt" "$base"
# A merged branch points at base (nothing un-promoted), so `git branch -d` is safe.
( cd "$repo" && "$RETIRE" "$merged_wt" --delete-branch ) >/dev/null 2>&1 \
  || fail "AC-5.1: retire --delete-branch must succeed on a merged foundry/fs/* branch"
[ ! -d "$merged_wt" ] || fail "AC-5.1: the worktree must be removed"
branch_exists "$merged_branch" && fail "AC-5.1: the merged branch must be deleted"

# --- AC-5.2: --delete-branch (no --force) refuses an UNMERGED branch.
unmerged_branch="foundry/fs/unmerged-demo"
unmerged_wt="$scratch/unmerged-wt"
git -C "$repo" worktree add -q -b "$unmerged_branch" "$unmerged_wt" "$base"
printf 'new work\n' > "$unmerged_wt/work.txt"
git -C "$unmerged_wt" add work.txt
git -C "$unmerged_wt" commit -qm "unmerged commit"

set +e
refuse_out="$( cd "$repo" && "$RETIRE" "$unmerged_wt" --delete-branch 2>&1 )"
refuse_code=$?
set -e
[ "$refuse_code" -ne 0 ] || fail "AC-5.2: must refuse to delete an unmerged branch without --force"
branch_exists "$unmerged_branch" || fail "AC-5.2: the unmerged branch must still exist after a refused delete"
case "$refuse_out" in
  *"$unmerged_branch"*) ;;
  *) fail "AC-5.2: the refusal must report the unmerged branch name" ;;
esac

# --- AC-5.3: --delete-branch --force deletes an unmerged branch (git -D).
# The worktree was already removed in the refused attempt above; recreate it on
# the SAME branch so --force can exercise the unmerged-delete path.
git -C "$repo" worktree prune
git -C "$repo" worktree add -q "$unmerged_wt" "$unmerged_branch"
( cd "$repo" && "$RETIRE" "$unmerged_wt" --delete-branch --force ) >/dev/null 2>&1 \
  || fail "AC-5.3: retire --delete-branch --force must delete an unmerged branch"
[ ! -d "$unmerged_wt" ] || fail "AC-5.3: the worktree must be removed under --force"
branch_exists "$unmerged_branch" && fail "AC-5.3: --force must delete the unmerged branch"

echo "worktree_retire_branch_test: PASS"
