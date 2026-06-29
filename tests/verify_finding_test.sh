#!/usr/bin/env bash
# Hermetic test for verify-finding.sh — NEVER builds/runs real code or lldb; it stubs the
# executor via VERIFY_EXEC_CMD and exercises the pure `decide` rule across every AC path.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="$REPO/plugins/foundry/scripts/verify-finding.sh"
fail() { echo "FAIL: $1" >&2; exit 1; }
eq() { [ "$1" = "$2" ] || fail "$3: expected '$2', got '$1'"; }
[ -x "$V" ] || fail "missing/!executable verify-finding.sh"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

# Mock executor: exit code by target keyword -> the run mapping (0/1/other).
cat > "$work/mock" <<'M'
#!/usr/bin/env bash
case "$2" in
  *repro*) exit 0 ;;   # reproduces  -> verified
  *clean*) exit 1 ;;   # disproved   -> refuted
  *)       exit 2 ;;   # can't run   -> unrunnable
esac
M
chmod +x "$work/mock"

# run via the seam: exit 0/1/other -> verified/refuted/unrunnable.
eq "$(VERIFY_EXEC_CMD="$work/mock" "$V" run native repro-case)"  verified   "seam reproduce->verified"
eq "$(VERIFY_EXEC_CMD="$work/mock" "$V" run native clean-case)"  refuted    "seam disprove->refuted"
eq "$(VERIFY_EXEC_CMD="$work/mock" "$V" run native odd-case)"    unrunnable "seam can't-run->unrunnable"

# run real path: the check command's exit code is the repro contract (0=reproduces).
eq "$("$V" run test  t 'true')"  verified   "real check exit0->verified"
eq "$("$V" run test  t 'false')" refuted    "real check exit1->refuted"
eq "$("$V" run snippet s '')"    unrunnable "real no-check->unrunnable"
eq "$("$V" run native x)"        unrunnable "native live-deferred->unrunnable"

# decide — the verify-by-execution rule across every AC path.
eq "$("$V" decide blocking no  -          yes)" block    "AC-1.4 non-executable blocking still blocks"
eq "$("$V" decide advisory no  -          yes)" advisory "AC-1.4 non-executable advisory stays advisory"
eq "$("$V" decide blocking yes -          no )" block    "AC-1.5 execution-off blocking keeps today's block"
eq "$("$V" decide blocking yes verified   yes)" block    "AC-1.1 verified blocking may block"
eq "$("$V" decide blocking yes refuted    yes)" drop     "AC-1.2 refuted drops"
eq "$("$V" decide blocking yes unrunnable yes)" advisory "AC-1.3 un-runnable blocking demotes to advisory"
eq "$("$V" decide advisory yes unrunnable yes)" advisory "advisory un-runnable stays advisory"
eq "$("$V" decide advisory yes verified   yes)" advisory "verified advisory stays advisory"

echo "verify_finding_test: PASS"
