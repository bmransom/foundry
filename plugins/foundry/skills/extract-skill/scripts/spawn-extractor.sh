#!/usr/bin/env bash
# Launch a same-harness skill drafting session from a brief.
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
  local harness="$1" prompt="$2"
  case "$harness" in
    claude) printf 'claude %s' "$(quote_prompt "$prompt")" ;;
    codex) printf 'codex %s' "$(quote_prompt "$prompt")" ;;
    pi) printf '%s %s' "${PI_AGENT_CMD:-pi}" "$(quote_prompt "$prompt")" ;;
    *) return 1 ;;
  esac
}

main() {
  local dry_run=0 print_harness=0
  while [ "$#" -gt 0 ]; do
    case "$1" in
      --dry-run) dry_run=1; shift ;;
      --print-harness) print_harness=1; shift ;;
      --) shift; break ;;
      -*) echo "spawn-extractor: unknown argument '$1'" >&2; exit 2 ;;
      *) break ;;
    esac
  done

  local harness
  harness="$(detect_harness)"
  if [ "$print_harness" -eq 1 ]; then printf '%s\n' "$harness"; exit 0; fi

  local skill="${1:?usage: spawn-extractor.sh [--dry-run] <skill-name> <brief-path> [project-dir]}"
  local brief="${2:?usage: spawn-extractor.sh [--dry-run] <skill-name> <brief-path> [project-dir]}"
  local dir="${3:-$PWD}"
  local slug="extract-$skill"
  local prompt="Read $brief in full. Draft or revise the skill described there using the Agent Skills format. Preserve reusable procedure, exclude non-reusable details, add realistic eval prompts, validate the structure, then report back."
  local pane_cmd
  if ! pane_cmd="$(agent_command "$harness" "$prompt")"; then
    echo "unknown harness - paste this prompt into a fresh agent session:" >&2
    echo "$prompt"
    exit 0
  fi

  read -r -a tmux_bin <<< "${AGENT_TMUX:-tmux}"
  emit() { if [ "$dry_run" -eq 1 ]; then printf '%s\n' "$*"; else "$@"; fi; }

  if [ -n "${TMUX:-}" ]; then
    slug="$(existing_names | dedupe "$slug")"
    emit "${tmux_bin[@]}" new-window -d -n "$slug" -c "$dir" "$pane_cmd"
    [ "$dry_run" -eq 1 ] || "${tmux_bin[@]}" display-message "extract-skill: spawned '$slug'"
    echo "spawned window: $slug"
  elif command -v "${tmux_bin[0]}" >/dev/null 2>&1; then
    slug="$(existing_names | dedupe "$slug")"
    emit "${tmux_bin[@]}" new-session -d -s "$slug" -c "$dir" "$pane_cmd"
    echo "spawned detached session: $slug"
    echo "attach with: ${tmux_bin[*]} attach -t $slug"
  else
    echo "tmux not found - run this manually:"
    echo "$pane_cmd"
  fi
}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then main "$@"; fi
