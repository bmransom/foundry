#!/usr/bin/env bash
# The PostToolUse adapter runs the convergence hook only for spec-file edits, surfaces
# FINDINGS to the agent (exit 2), and is fail-safe everywhere else (exit 0).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADAPTER="$REPO/plugins/foundry/scripts/spec-convergence-posttooluse.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
[ -f "$ADAPTER" ] || fail "missing spec-convergence-posttooluse.sh"

work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
cat > "$work/stub" <<'STUB'
#!/usr/bin/env bash
v="$(head -1 "$STUB_SEQ")"; tail -n +2 "$STUB_SEQ" > "$STUB_SEQ.t"; mv "$STUB_SEQ.t" "$STUB_SEQ"
if [ "$v" = CLEAN ]; then echo "(no findings)"; echo "SPEC_REVIEW: CLEAN"
else echo "FLAGGED: hedge-word in design.md"; echo "SPEC_REVIEW: FINDINGS"; fi
STUB
chmod +x "$work/stub"
export SPEC_CONVERGENCE_REVIEW_CMD="$work/stub"

run() {  # $1 = stdin payload; captures OUT + RC
  set +e
  OUT="$(printf '%s' "$1" | bash "$ADAPTER" 2>&1)"; RC=$?
  set -e
}

SPEC='{"tool_input":{"file_path":"/x/roadmap/specs/foo/design.md"}}'

# spec edit + FINDINGS -> surface to the agent (exit 2)
export SPEC_CONVERGENCE_STATE="$work/s1" STUB_SEQ="$work/q1"; printf 'FINDINGS\n' > "$STUB_SEQ"
run "$SPEC"
[ "$RC" -eq 2 ] || fail "spec+FINDINGS expected exit 2, got $RC: $OUT"
case "$OUT" in *FLAGGED:*) ;; *) fail "findings not surfaced: $OUT" ;; esac

# spec edit + CLEAN -> no-op (exit 0)
export SPEC_CONVERGENCE_STATE="$work/s2" STUB_SEQ="$work/q2"; printf 'CLEAN\n' > "$STUB_SEQ"
run "$SPEC"
[ "$RC" -eq 0 ] || fail "spec+CLEAN expected exit 0, got $RC: $OUT"

# non-spec edit -> no-op, hook never runs
export SPEC_CONVERGENCE_STATE="$work/s3" STUB_SEQ="$work/q3"; printf 'FINDINGS\n' > "$STUB_SEQ"
run '{"tool_input":{"file_path":"/x/src/main.py"}}'
[ "$RC" -eq 0 ] || fail "non-spec edit expected exit 0, got $RC: $OUT"
[ -s "$STUB_SEQ" ] || fail "non-spec edit must not consume a review (hook ran)"

# malformed payload -> no-op
run 'not json at all'
[ "$RC" -eq 0 ] || fail "malformed payload expected exit 0, got $RC: $OUT"

echo "spec_convergence_posttooluse_test: PASS"
