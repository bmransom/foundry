#!/usr/bin/env bash
# Build the seeded-bug fixture with debug info. ASan (default) traps the
# out-of-bounds write at the faulting line; pass `plain` for a vanilla build.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${2:-/tmp/buggy}"
CC="${CC:-cc}"
case "${1:-asan}" in
  asan)  "$CC" -g -O1 -fno-inline -fsanitize=address "$HERE/buggy.c" -o "$OUT" ;;
  plain) "$CC" -g -O0 "$HERE/buggy.c" -o "$OUT" ;;
  *) echo "usage: build.sh [asan|plain] [out]" >&2; exit 2 ;;
esac
echo "$OUT"
