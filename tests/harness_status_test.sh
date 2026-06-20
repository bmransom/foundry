#!/usr/bin/env bash
# Unit checks for the shared harness availability status helper.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATUS="$REPO/plugins/foundry/scripts/harness-status.py"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[ -f "$STATUS" ] || fail "missing harness-status.py"

fixture="$(mktemp -d)"
trap 'rm -rf "$fixture"' EXIT

python3 - "$STATUS" "$fixture" <<'PY'
import importlib.util
import json
import pathlib
import sys

status_path = pathlib.Path(sys.argv[1])
fixture = pathlib.Path(sys.argv[2])

spec = importlib.util.spec_from_file_location("harness_status", status_path)
status = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(status)


def assert_equal(actual, expected, message):
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


expected_categories = {
    "ok",
    "missing-command",
    "not-authenticated",
    "subscription-unavailable",
    "usage-limited",
    "rate-limited",
    "unknown-failure",
}
assert_equal(status.STATUS_CATEGORIES, expected_categories, "harness availability category set")

missing = status.check_harness(
    "codex",
    command_exists=lambda name: False,
    runner=lambda command, timeout_s: status.CommandResult(0, "", ""),
)
assert_equal(missing["category"], "missing-command", "missing command category")
assert_equal(missing["command"], "codex", "missing command name")

ok_commands = []


def ok_runner(command, timeout_s):
    ok_commands.append(command)
    return status.CommandResult(0, "OK\n", "")


ok = status.check_harness(
    "codex",
    command_exists=lambda name: name == "codex",
    runner=ok_runner,
)
assert_equal(ok["category"], "ok", "codex ok category")
assert_equal(ok_commands, [["codex", "login", "status"], ["codex", "doctor", "--json"]], "codex probes")

auth = status.check_harness(
    "claude-code",
    command_exists=lambda name: name == "claude",
    runner=lambda command, timeout_s: status.CommandResult(1, "", "login required for jane@example.com"),
)
assert_equal(auth["category"], "not-authenticated", "auth category")
assert "jane@example.com" not in auth["detail"], "email redacted"
assert "[redacted-email]" in auth["detail"], "redaction marker"

subscription = status.check_harness(
    "claude-code",
    command_exists=lambda name: name == "claude",
    runner=lambda command, timeout_s: status.CommandResult(1, "subscription unavailable", ""),
)
assert_equal(subscription["category"], "subscription-unavailable", "subscription category")

usage = status.check_harness(
    "codex",
    command_exists=lambda name: name == "codex",
    runner=lambda command, timeout_s: status.CommandResult(1, "usage limit reached", ""),
)
assert_equal(usage["category"], "usage-limited", "usage category")

rate = status.check_harness(
    "codex",
    command_exists=lambda name: name == "codex",
    runner=lambda command, timeout_s: status.CommandResult(1, "rate limit, retry later", ""),
)
assert_equal(rate["category"], "rate-limited", "rate category")

unknown = status.check_harness(
    "codex",
    command_exists=lambda name: name == "codex",
    runner=lambda command, timeout_s: status.CommandResult(2, "unexpected failure", ""),
)
assert_equal(unknown["category"], "unknown-failure", "unknown category")

results = status.check_selected_harnesses(
    repo_root=fixture,
    harnesses=["codex", "claude-code"],
    command_exists=lambda name: name in {"codex", "claude"},
    runner=lambda command, timeout_s: status.CommandResult(0, "OK\n", ""),
)
assert_equal([item["harness"] for item in results], ["codex", "claude-code"], "selected harness order")
written = json.loads((fixture / ".foundry/tmp/harness-status/status.json").read_text(encoding="utf-8"))
assert_equal([item["category"] for item in written["harnesses"]], ["ok", "ok"], "written categories")
PY

echo "harness_status_test: PASS"
