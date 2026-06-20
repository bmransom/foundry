#!/usr/bin/env bash
# Eval sandbox gate: every eval flow that mutates git config must operate on a
# clone/copy, never the real repo. The recorded corruption came from a PYTHON
# config-mutating flow, so the gate exercises a Python config writer (not just a
# *.sh script) and asserts the real repo's .git/config is byte-identical before
# and after. A seeded defect — a Python writer that mutates the real config — is
# caught.
#
# Hermetic: needs only git and python3.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SANDBOX="$REPO/evals/harness/eval_sandbox.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$SANDBOX" ] || fail "missing eval sandbox helper evals/harness/eval_sandbox.py"

scratch="$(mktemp -d)"
realrepo="$scratch/realrepo"
trap 'rm -rf "$scratch"' EXIT

# A stand-in for the real repo, so the test never touches foundry's own .git.
git init -q -b main "$realrepo"
git -C "$realrepo" config user.email "real@foundry.test"
git -C "$realrepo" config user.name "Real Foundry"
printf '# real\n' > "$realrepo/README.md"
git -C "$realrepo" add README.md
git -C "$realrepo" commit -qm "initial"

config_path="$realrepo/.git/config"
before="$(cksum < "$config_path")"

# --- Sandboxed Python config writer: mutates git config inside a sandbox copy.
# The real repo's .git/config must be byte-identical afterward.
sandboxed_flow="$scratch/sandboxed_flow.py"
cat > "$sandboxed_flow" <<PY
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("$SANDBOX").parent))
import eval_sandbox

real = Path("$realrepo")
with eval_sandbox.sandbox_repo(real) as sandbox:
    assert sandbox.resolve() != real.resolve(), "sandbox must be a separate tree"
    # The recorded corruption: flip core.bare and overwrite [user] — but on the
    # SANDBOX copy, never the real repo.
    subprocess.run(["git", "-C", str(sandbox), "config", "core.bare", "true"], check=True)
    subprocess.run(["git", "-C", str(sandbox), "config", "user.name", "foundry-eval"], check=True)
    subprocess.run(["git", "-C", str(sandbox), "config", "user.email", "eval@foundry.local"], check=True)
PY

python3 "$sandboxed_flow" || fail "the sandboxed Python flow must run successfully"
after_ok="$(cksum < "$config_path")"
[ "$before" = "$after_ok" ] \
  || fail "AC-7.2: the real repo's .git/config must be byte-identical after a SANDBOXED Python config flow"

# --- Seeded defect: a Python config writer that mutates the REAL repo's config
# (no sandbox), run UNDER guard_real_config. The guard must catch it by raising
# RealConfigMutated — proving the mechanism discriminates against the recorded
# failure mode, not just that an unsandboxed write happens to change bytes.
seeded_defect="$scratch/seeded_defect.py"
cat > "$seeded_defect" <<PY
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path("$SANDBOX").parent))
import eval_sandbox

real = "$realrepo"
try:
    with eval_sandbox.guard_real_config(real):
        # The recorded failure mode, applied to the REAL repo (the defect).
        subprocess.run(["git", "-C", real, "config", "core.bare", "true"], check=True)
        subprocess.run(["git", "-C", real, "config", "user.name", "foundry-eval"], check=True)
except eval_sandbox.RealConfigMutated:
    print("guard-caught")
    sys.exit(0)
print("guard-missed")
sys.exit(1)
PY

guard_out="$(python3 "$seeded_defect")" \
  || fail "discrimination: guard_real_config must raise RealConfigMutated when a seeded Python flow mutates the real repo's .git/config"
[ "$guard_out" = "guard-caught" ] \
  || fail "discrimination: the guard must catch the seeded real-config mutation (got: $guard_out)"

echo "eval_sandbox_test: PASS"
