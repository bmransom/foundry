#!/usr/bin/env bash
# Spawn the same agent harness in a fresh tmux session/window from a prompt file.
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
  prompt_dir=".foundry/tmp/fresh-session/$session_id"
  prompt_file="$prompt_dir/prompt.md"
  short_prompt="Read $prompt_file and follow it exactly."

  if ! pane_cmd="$(agent_command "$harness" "$skip" "$short_prompt")"; then
    echo "unknown harness - paste this prompt into a fresh agent session:" >&2
    echo "$prompt"
    exit 0
  fi

  if [ "$dry_run" -eq 0 ]; then
    mkdir -p "$dir/$prompt_dir"
    printf '%s\n' "$prompt" > "$dir/$prompt_file"
  fi

  read -r -a tmux_bin <<< "${AGENT_TMUX:-tmux}"
  emit() { if [ "$dry_run" -eq 1 ]; then printf '%s\n' "$*"; else "$@"; fi; }

  if [ -n "${TMUX:-}" ]; then
    slug="$(existing_names | dedupe "$slug")"
    emit "${tmux_bin[@]}" new-window -d -n "$slug" -c "$dir" "$pane_cmd"
    [ "$dry_run" -eq 1 ] || "${tmux_bin[@]}" display-message "fresh-session: spawned '$slug'"
    echo "spawned window: $slug"
    echo "prompt: $prompt_file"
  elif command -v "${tmux_bin[0]}" >/dev/null 2>&1; then
    slug="$(existing_names | dedupe "$slug")"
    emit "${tmux_bin[@]}" new-session -d -s "$slug" -c "$dir" "$pane_cmd"
    echo "spawned detached session: $slug"
    echo "attach with: ${tmux_bin[*]} attach -t $slug"
    echo "prompt: $prompt_file"
  else
    echo "tmux not found - run this manually:"
    echo "$pane_cmd"
    echo "prompt: $prompt_file"
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
