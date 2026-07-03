"""Gate suite (design D5, AC-5.2): board + prose + knowledge checks, then the repo's
`[gate].commands`. Collects one finding per failure; the last line is exactly
`gate: PASS` or `gate: FAIL`.

`[gate].commands` entries are shell-safe argv (design D3's config, no shell string) —
each is split with `shlex.split` and run as a subprocess with no shell, judged by exit
status. A repo with no `.foundry/config.toml` (or an empty `[gate].commands`) runs the
three ported checks only — that is a valid, passing configuration, not a gap.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from foundry.config import Config, ConfigError
from foundry.env import consumer_env
from foundry.gate import board, knowledge, prose

CHECKS = (board.check, prose.check, knowledge.check)


def run(repo_root: Path | str) -> tuple[bool, list[str]]:
    """Run the gate suite. Returns (ok, lines) where `lines` is every finding/skip
    note in order, followed by the terminal `gate: PASS`/`gate: FAIL` line.
    """
    repo_root = Path(repo_root)
    lines: list[str] = []
    failed = False

    for check in CHECKS:
        ok, findings = check(repo_root)
        lines.extend(findings)
        if not ok:
            failed = True

    try:
        config = Config.load(repo_root)
    except ConfigError as e:
        lines.append(f"gate: config: {e}")
        failed = True
    else:
        for command in config.gate_commands:
            argv = shlex.split(command)
            # The repo's env, not foundry's: under `uvx foundry gate` the venv
            # would otherwise shadow the consumer's python3 (foundry.env).
            result = subprocess.run(argv, cwd=repo_root, env=consumer_env())
            if result.returncode != 0:
                failed = True
                lines.append(f"gate: command failed ({command}): exit {result.returncode}")

    lines.append("gate: FAIL" if failed else "gate: PASS")
    return not failed, lines
