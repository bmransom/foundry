#!/usr/bin/env python3
"""Classify local availability for manifest-selected Foundry harnesses."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


STATUS_CATEGORIES = {
    "ok",
    "missing-command",
    "not-authenticated",
    "subscription-unavailable",
    "usage-limited",
    "rate-limited",
    "unknown-failure",
}

COMMAND_BY_HARNESS = {
    "codex": "codex",
    "claude-code": "claude",
}

PROBES_BY_HARNESS = {
    "codex": [["codex", "login", "status"], ["codex", "doctor", "--json"]],
    "claude-code": [["claude", "auth", "status"]],
}


class CommandResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


def check_harness(
    harness: str,
    *,
    command_exists: Callable[[str], bool] | None = None,
    runner: Callable[[list[str], int], CommandResult] | None = None,
    timeout_s: int = 10,
) -> dict[str, object]:
    command_exists = command_exists or _command_exists
    runner = runner or _run_command
    command = COMMAND_BY_HARNESS.get(harness, harness)

    if not command_exists(command):
        return {
            "harness": harness,
            "category": "missing-command",
            "command": command,
            "detail": f"{command} is not on PATH",
        }

    probes = PROBES_BY_HARNESS.get(harness, [[command, "--version"]])
    for probe in probes:
        result = runner(probe, timeout_s)
        if result.exit_code != 0:
            detail = _redact(f"{result.stdout}\n{result.stderr}".strip())
            return {
                "harness": harness,
                "category": _classify_failure(detail),
                "command": " ".join(probe),
                "detail": detail,
            }

    return {
        "harness": harness,
        "category": "ok",
        "command": command,
        "detail": "all probes passed",
    }


def check_selected_harnesses(
    *,
    repo_root: Path | str,
    harnesses: list[str],
    command_exists: Callable[[str], bool] | None = None,
    runner: Callable[[list[str], int], CommandResult] | None = None,
    timeout_s: int = 10,
) -> list[dict[str, object]]:
    repo = Path(repo_root)
    results = [
        check_harness(
            harness,
            command_exists=command_exists,
            runner=runner,
            timeout_s=timeout_s,
        )
        for harness in harnesses
    ]
    output = {
        "created_at": _utc_now(),
        "harnesses": results,
    }
    status_dir = repo / ".foundry/tmp/harness-status"
    status_dir.mkdir(parents=True, exist_ok=True)
    (status_dir / "status.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return results


def _classify_failure(detail: str) -> str:
    text = detail.lower()
    if "rate limit" in text or "rate-limited" in text:
        return "rate-limited"
    if "usage limit" in text or "quota" in text or "usage cap" in text:
        return "usage-limited"
    if "subscription" in text or "plan disabled" in text or "not available on" in text:
        return "subscription-unavailable"
    if "not authenticated" in text or "login required" in text or "log in" in text:
        return "not-authenticated"
    return "unknown-failure"


def _redact(text: str) -> str:
    return re.sub(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "[redacted-email]",
        text,
    )


def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _run_command(command: list[str], timeout_s: int) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or "timed out")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_root")
    parser.add_argument("harnesses", nargs="+")
    args = parser.parse_args(argv)

    results = check_selected_harnesses(
        repo_root=args.repo_root,
        harnesses=args.harnesses,
    )
    print(json.dumps({"harnesses": results}, indent=2, sort_keys=True))
    return 0 if all(item["category"] == "ok" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
