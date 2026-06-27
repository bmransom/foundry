#!/usr/bin/env bash
# Footer algebra — the finding-set operations on the FLAGGED footer, keyed on ONE
# normalized signature so the inner loop (union) and the refuter recompute (difference)
# dedup identically (AC-12.5). The key = lowercase + collapsed internal whitespace +
# trim; membership is EXACT on that key (whole-line, fixed-string), never a prefix or
# substring match, so AC-2.1 and AC-2.10 never collide.
#
# Usage:
#   footer-algebra.sh union <report-or-footer-file>...        merged FLAGGED lines, deduped, first-seen order
#   footer-algebra.sh difference <report-file> [refuter-file]  surviving FLAGGED lines + CODE_REVIEW verdict
#       (difference removes a FLAGGED line whose key matches a refuter `DROP <sig>`;
#        DROP-only — the refuter can remove a finding, never add one)
set -euo pipefail

normalize() { printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -s '[:space:]' ' ' | sed -E 's/^ //; s/ $//'; }

cmd="${1:?usage: footer-algebra.sh union|difference ...}"; shift

case "$cmd" in
  union)
    seen=""
    for f in "$@"; do
      [ -f "$f" ] || continue
      while IFS= read -r line; do
        case "$line" in FLAGGED:*) ;; *) continue ;; esac
        key="$(normalize "${line#FLAGGED:}")"
        printf '%s\n' "$seen" | grep -Fxq -- "$key" && continue
        seen="${seen}${key}
"
        printf '%s\n' "$line"
      done < "$f"
    done
    ;;
  difference)
    report="${1:?footer-algebra.sh difference <report-file> [refuter-file]}"
    refuter="${2:-/dev/null}"
    drops=""
    while IFS= read -r d; do
      [ -n "$d" ] || continue
      drops="${drops}$(normalize "$d")
"
    done < <(grep -E '^DROP[[:space:]]' "$refuter" 2>/dev/null | sed -E 's/^DROP[[:space:]]+//' || true)
    fail=0
    while IFS= read -r line; do
      case "$line" in FLAGGED:*) ;; *) continue ;; esac
      key="$(normalize "${line#FLAGGED:}")"
      printf '%s\n' "$drops" | grep -Fxq -- "$key" && continue
      printf '%s\n' "$line"; fail=1
    done < <(grep -E '^FLAGGED:' "$report" 2>/dev/null || true)
    [ "$fail" -eq 1 ] && echo "CODE_REVIEW: FAIL" || echo "CODE_REVIEW: PASS"
    ;;
  *)
    echo "footer-algebra.sh: unknown command '$cmd' (expected: union | difference)" >&2
    exit 2 ;;
esac
