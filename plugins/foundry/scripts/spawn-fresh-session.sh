#!/usr/bin/env bash
# Spawn the same agent harness in a fresh tmux session/window from a prompt file.
#
# Isolation: each spawn runs in its own git worktree on branch foundry/fs/<id>,
# so concurrent sessions never collide on the working tree or branch. Isolation
# is default-on; there is no opt-in flag.
#
# CAVEAT — worktrees SHARE .git/config. Linked worktrees share the common git
# dir, so `git config --local` and `core.bare` writes reach the SHARED
# .git/config; the worktree does NOT isolate it. The per-session
# GIT_CONFIG_GLOBAL set below is a guardrail for GLOBAL-config writes, not a
# boundary, and no PATH git shim is installed (a shim is brittle and gives false
# assurance). Full .git/config isolation needs a per-session clone (deferred).
set -euo pipefail

existing_names() {
  read -r -a tb <<< "${AGENT_TMUX:-tmux}"
  "${tb[@]}" list-windows -a -F '#{window_name}' 2>/dev/null || true
}

dedupe() {
  local base="$1" name="$1" n=2 existing
  existing="$(cat)"
  while printf '%s\n' "$existing" | grep -qxF -- "$name"; do
    name="${base}-${n}"
    n=$((n + 1))
  done
  printf '%s' "$name"
}

parent_cmd() {
  if [ -n "${AGENT_PARENT_CMD:-}" ]; then printf '%s' "$AGENT_PARENT_CMD"; return; fi
  ps -o comm= -o args= -p "${PPID:-0}" 2>/dev/null || true
}

detect_harness() {
  case "${AGENT_HARNESS:-}" in
    claude|codex|pi) printf '%s\n' "$AGENT_HARNESS"; return ;;
    "") ;;
    *) printf 'unknown\n'; return ;;
  esac
  if [ -n "${CODEX_THREAD_ID:-}" ] || [ -n "${CODEX_CI:-}" ]; then printf 'codex\n'; return; fi
  if env | grep -q '^CLAUDE'; then printf 'claude\n'; return; fi
  if env | grep -q '^PI_'; then printf 'pi\n'; return; fi
  case "$(parent_cmd)" in
    *codex*) printf 'codex\n' ;;
    *claude*) printf 'claude\n' ;;
    *pi-coding-agent*|*" pi "*) printf 'pi\n' ;;
    *) printf 'unknown\n' ;;
  esac
}

quote_prompt() {
  local s="$1"
  printf "'%s'" "${s//\'/\'\\\'\'}"
}

agent_command() {
  local harness="$1" skip="$2" prompt="$3"
  case "$harness" in
    claude)
      local cmd="claude"
      [ "$skip" -eq 1 ] && cmd+=" --dangerously-skip-permissions"
      printf '%s %s' "$cmd" "$(quote_prompt "$prompt")"
      ;;
    codex)
      local cmd="codex"
      [ "$skip" -eq 1 ] && cmd+=" --dangerously-bypass-approvals-and-sandbox"
      printf '%s %s' "$cmd" "$(quote_prompt "$prompt")"
      ;;
    pi) printf '%s %s' "${PI_AGENT_CMD:-pi}" "$(quote_prompt "$prompt")" ;;
    *) return 1 ;;
  esac
}

is_git_repo() { git -C "$1" rev-parse --git-dir >/dev/null 2>&1; }

# Linked worktree iff --git-dir differs from --git-common-dir.
in_linked_worktree() {
  local git_dir common_dir
  git_dir="$(git -C "$1" rev-parse --git-dir 2>/dev/null)" || return 1
  common_dir="$(git -C "$1" rev-parse --git-common-dir 2>/dev/null)" || return 1
  [ "$git_dir" != "$common_dir" ]
}

# The commit origin/HEAD resolves to, then main, then HEAD — no network fetch.
resolve_base() {
  git -C "$1" rev-parse --verify -q origin/HEAD \
    || git -C "$1" rev-parse --verify -q main \
    || git -C "$1" rev-parse --verify -q HEAD
}

usage() {
  echo "usage: spawn-fresh-session.sh [--dry-run] [--print-harness] [--skip-permissions] --name <slug> [project-dir] < prompt.md" >&2
}

main() {
  local dry_run=0 print_harness=0 skip=0 slug="fresh-session"
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1; shift ;;
      --print-harness) print_harness=1; shift ;;
      --skip-permissions|--yolo) skip=1; shift ;;
      --name)
        [ "$#" -ge 2 ] || { usage; exit 2; }
        slug="$2"
        shift 2
        ;;
      --) shift; break ;;
      -*) echo "spawn-fresh-session: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done
  case "${AGENT_SKIP_PERMISSIONS:-}" in 1|true|yes) skip=1 ;; esac

  local harness
  harness="$(detect_harness)"
  if [ "$print_harness" -eq 1 ]; then printf '%s\n' "$harness"; exit 0; fi

  local dir="${1:-$PWD}"
  local prompt
  prompt="$(cat)"
  [ -n "$prompt" ] || { echo "spawn-fresh-session: prompt stdin is required" >&2; exit 2; }

  local safe_slug="${slug//[^[:alnum:]._-]/-}"
  local session_id prompt_dir prompt_file short_prompt pane_cmd
  session_id="$(date +%Y%m%d%H%M%S)-$safe_slug-$$"
  # Support files (prompt, per-session gitconfig) live in the PRIMARY session
  # dir under gitignored .foundry/tmp/, so they survive worktree retire and do
  # not ride the ephemeral branch. The harness reads the prompt by absolute path.
  prompt_dir=".foundry/tmp/fresh-session/$session_id"
  prompt_file="$prompt_dir/prompt.md"
  local abs_prompt_file="$dir/$prompt_file"
  short_prompt="Read $abs_prompt_file and follow it exactly."

  if ! pane_cmd="$(agent_command "$harness" "$skip" "$short_prompt")"; then
    echo "unknown harness - paste this prompt into a fresh agent session:" >&2
    echo "$prompt"
    exit 0
  fi

  # --- Isolation: create a per-session worktree and launch the harness there.
  # The source tree is never the harness cwd, so concurrent sessions never
  # collide on the working tree or branch. Isolation is default-on (AC-1.7);
  # there is no opt-in flag. dry-run is a preview and creates no git state.
  local worktree="$dir" branch="" session_gitconfig=""
  if [ "$dry_run" -eq 0 ]; then
    if ! is_git_repo "$dir"; then
      # No git, no worktree. Refuse loudly unless explicitly allowed.
      case "${FOUNDRY_SPAWN_ALLOW_NON_GIT:-}" in
        1|true|yes)
          echo "spawn-fresh-session: WARNING — '$dir' is not a git repo; spawning in place with NO worktree and NO branch. Isolation is lost; concurrent sessions can collide." >&2
          ;;
        *)
          echo "spawn-fresh-session: REFUSING to spawn — '$dir' is not a git repo, so no worktree isolation is possible. Set FOUNDRY_SPAWN_ALLOW_NON_GIT=1 to spawn in place anyway (isolation lost)." >&2
          exit 1
          ;;
      esac
      mkdir -p "$dir/$prompt_dir"
      printf '%s\n' "$prompt" > "$abs_prompt_file"
    else
      command -v git >/dev/null 2>&1 \
        && git worktree --help >/dev/null 2>&1 \
        || { echo "spawn-fresh-session: git worktree is unavailable" >&2; exit 1; }

      mkdir -p "$dir/$prompt_dir"
      printf '%s\n' "$prompt" > "$abs_prompt_file"

      if in_linked_worktree "$dir"; then
        # Handoff from a linked worktree: reuse it; never mint a new one, so the
        # successor keeps the parent's uncommitted WIP (AC-2.1, AC-2.3).
        worktree="$dir"
      else
        # Fresh session or a primary-tree handoff: promote to a new worktree.
        worktree="$dir/$prompt_dir/worktree"
        branch="foundry/fs/$session_id"
        local base
        base="$(resolve_base "$dir")" \
          || { echo "spawn-fresh-session: cannot resolve a worktree base (origin/HEAD, main, HEAD)" >&2; exit 1; }
        if ! git -C "$dir" worktree add -b "$branch" "$worktree" "$base" >/dev/null 2>&1; then
          # Roll back any partial state; never start tmux on a failed add.
          rm -rf "$worktree"
          if git -C "$dir" rev-parse --verify -q "$branch" >/dev/null 2>&1; then
            git -C "$dir" branch -D "$branch" >/dev/null 2>&1 || true
          fi
          echo "spawn-fresh-session: git worktree add failed for $branch" >&2
          exit 1
        fi
      fi

      # Guardrail (not a boundary): a per-session GIT_CONFIG_GLOBAL so a
      # session's GLOBAL-config writes land in a throwaway file. Linked
      # worktrees still SHARE .git/config; `git config --local` and core.bare
      # writes reach the shared file and this guardrail does NOT isolate it.
      session_gitconfig="$dir/$prompt_dir/gitconfig"
      : > "$session_gitconfig"
    fi
  fi

  read -r -a tmux_bin <<< "${AGENT_TMUX:-tmux}"
  emit() { if [ "$dry_run" -eq 1 ]; then printf '%s\n' "$*"; else "$@"; fi; }

  if [ -n "${TMUX:-}" ]; then
    slug="$(existing_names | dedupe "$slug")"
    if [ -n "$session_gitconfig" ]; then
      emit env GIT_CONFIG_GLOBAL="$session_gitconfig" "${tmux_bin[@]}" new-window -d -n "$slug" -c "$worktree" -e GIT_CONFIG_GLOBAL="$session_gitconfig" "$pane_cmd"
    else
      emit "${tmux_bin[@]}" new-window -d -n "$slug" -c "$worktree" "$pane_cmd"
    fi
    [ "$dry_run" -eq 1 ] || "${tmux_bin[@]}" display-message "fresh-session: spawned '$slug'"
    echo "spawned window: $slug"
    echo "prompt: $abs_prompt_file"
    if [ -n "$branch" ]; then echo "worktree: $worktree (branch $branch)"; fi
  elif command -v "${tmux_bin[0]}" >/dev/null 2>&1; then
    slug="$(existing_names | dedupe "$slug")"
    if [ -n "$session_gitconfig" ]; then
      emit env GIT_CONFIG_GLOBAL="$session_gitconfig" "${tmux_bin[@]}" new-session -d -s "$slug" -c "$worktree" -e GIT_CONFIG_GLOBAL="$session_gitconfig" "$pane_cmd"
    else
      emit "${tmux_bin[@]}" new-session -d -s "$slug" -c "$worktree" "$pane_cmd"
    fi
    echo "spawned detached session: $slug"
    echo "attach with: ${tmux_bin[*]} attach -t $slug"
    echo "prompt: $abs_prompt_file"
    if [ -n "$branch" ]; then echo "worktree: $worktree (branch $branch)"; fi
  else
    echo "tmux not found - run this manually:"
    echo "cd $worktree && $pane_cmd"
    echo "prompt: $abs_prompt_file"
    if [ -n "$branch" ]; then echo "worktree: $worktree (branch $branch)"; fi
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
