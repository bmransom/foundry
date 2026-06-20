#!/usr/bin/env bash
# Discrimination check: the v1 commands advertised in SKILL.md must equal the
# broker's implemented subcommands (and round must carry its flags). This is the
# test that would have caught `round` being advertised but never wired.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BROKER="$REPO/plugins/foundry/scripts/harness-deliberation-broker.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$BROKER" ] || fail "missing broker script"

python3 - "$BROKER" "$REPO" <<'PY'
import pathlib
import re
import subprocess
import sys

broker = pathlib.Path(sys.argv[1])
repo = pathlib.Path(sys.argv[2])
skill = (repo / "plugins/foundry/skills/harness-deliberation/SKILL.md").read_text(encoding="utf-8")

# Canonical source: the bullets under "## V1 Commands" in SKILL.md.
advertised = set()
in_section = False
for line in skill.splitlines():
    if line.strip().startswith("## "):
        in_section = line.strip() == "## V1 Commands"
        continue
    if in_section:
        match = re.match(r"\s*-\s+`([a-z-]+)", line)
        if match:
            advertised.add(match.group(1))

# Implemented: argparse lists the valid subcommands when given an invalid choice.
proc = subprocess.run([sys.executable, str(broker), "__invalid__"], capture_output=True, text=True)
choices = re.search(r"choose from (.+?)\)", proc.stderr)
assert choices, f"could not parse subcommands from: {proc.stderr!r}"
implemented = set(re.findall(r"'?([a-z-]+)'?", choices.group(1)))

assert advertised, "no advertised commands parsed from SKILL.md"
assert implemented, "no implemented subcommands parsed from the broker"

missing = advertised - implemented  # advertised but unwired -> the round bug
extra = implemented - advertised
assert not missing, f"advertised in SKILL.md but not implemented: {sorted(missing)}"
assert not extra, f"implemented but not advertised in SKILL.md: {sorted(extra)}"

# Options matter too: a flagless `round` must fail. Assert its flags are present.
help_proc = subprocess.run(
    [sys.executable, str(broker), "round", "--help"], capture_output=True, text=True
)
assert "--session-dir" in help_proc.stdout, "round --help must expose --session-dir"
assert "--timeout-s" in help_proc.stdout, "round --help must expose --timeout-s"

# Discrimination self-check: a doc-only command (advertised, unimplemented) is caught.
assert (advertised | {"bogus-doc-command"}) - implemented == {"bogus-doc-command"}, (
    "the comparison must flag a doc-only command"
)
print("command surface OK:", sorted(implemented))
PY

echo "harness_deliberation_command_surface_test: PASS"
