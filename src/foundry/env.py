"""Consumer-environment sanitation.

Foundry often runs from an isolated interpreter (`uvx foundry gate`, `uv run
foundry`): that interpreter's bin dir leads PATH and VIRTUAL_ENV points at its
venv. Commands that belong to the consumer repo — `[gate].commands`, `[gate].test`,
stage hooks — must run in the repo's own environment, or their `python3` resolves
to foundry's interpreter and repo tooling (ruff, pytest) goes missing.
"""

from __future__ import annotations

import os
import sys


def consumer_env() -> dict:
    """os.environ minus foundry's interpreter leakage: VIRTUAL_ENV dropped, the
    running interpreter's bin dirs removed from PATH. Everything else passes
    through untouched."""
    env = dict(os.environ)
    env.pop("VIRTUAL_ENV", None)
    foundry_bins = {
        os.path.dirname(sys.executable),
        os.path.join(sys.prefix, "bin"),
        os.path.join(sys.exec_prefix, "bin"),
    }
    path = env.get("PATH", "")
    kept = [p for p in path.split(os.pathsep) if p and p not in foundry_bins]
    env["PATH"] = os.pathsep.join(kept)
    return env
