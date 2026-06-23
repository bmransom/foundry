#!/usr/bin/env bash
# Skill-spawned tmux sessions/windows carry a reserved prefix (default `foundry-`)
# so they are distinguishable from ad-hoc sessions and bulk-cleanable
# (`tmux ls | grep '^foundry-'`). Idempotent; overridable via FOUNDRY_TMUX_PREFIX.
set -euo pipefail

# Hermetic against the git-hook env (GIT_DIR etc. would hijack the fixture repo).
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY GIT_PREFIX \
      GIT_CONFIG_PARAMETERS GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM 2>/dev/null || true

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$REPO/plugins/foundry/scripts/spawn-fresh-session.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -x "$RUNNER" ] || fail "missing shared fresh-session runner"

repo="$(mktemp -d)"; trap 'rm -rf "$repo"' EXIT
git -C "$repo" init -q
git -C "$repo" config user.email t@example.com
git -C "$repo" config user.name t
git -C "$repo" commit -q --allow-empty -m init

spawn() {  # $1 = --name ; runs inside a (fake) tmux so the new-window path is taken
  printf 'p\n' | TMUX=1 AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
    "$RUNNER" --dry-run --name "$1" "$repo" 2>&1
}

# Default prefix on the spawned window name.
out="$(spawn spec-review)"
case "$out" in *new-window*foundry-spec-review*) ;; *) fail "tmux name must carry the foundry- prefix: $out" ;; esac

# Idempotent: an already-prefixed name is not doubled.
out2="$(spawn foundry-deliberate)"
case "$out2" in *foundry-foundry-*) fail "double-prefixed: $out2" ;; esac
case "$out2" in *foundry-deliberate*) ;; *) fail "expected foundry-deliberate: $out2" ;; esac

# Overridable prefix.
out3="$(printf 'p\n' | TMUX=1 FOUNDRY_TMUX_PREFIX=fdry- AGENT_HARNESS=claude AGENT_TMUX=/bin/echo \
  "$RUNNER" --dry-run --name spec-review "$repo" 2>&1)"
case "$out3" in *fdry-spec-review*) ;; *) fail "FOUNDRY_TMUX_PREFIX override broken: $out3" ;; esac

echo "fresh_session_tmux_marker_test: PASS"
