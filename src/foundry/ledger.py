"""Run ledger: wide events, append-only, gitignored (design D4).

Events land at .foundry/runs/<run-id>/events.jsonl, one JSON object per line.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

EVENT_NAMES = (
    "run_started",
    "stage_started",
    "stage_completed",
    "gate_evaluated",
    "hook_evaluated",
    "run_halted",
    "run_resumed",
    "run_completed",
)

# $/Mtok (input, output). Unknown model -> tokens recorded, cost_usd None.
PRICES: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (15.0, 75.0),
    "claude-sonnet-5": (3.0, 15.0),
}
PRICES_UPDATED = "2026-07-02"


def compute_cost(model: str | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if model not in PRICES or input_tokens is None or output_tokens is None:
        return None
    price_in, price_out = PRICES[model]
    return (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out


def new_run_id(now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"r-{now.strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2)}"


@dataclass
class RunEvent:
    """A D4 wide event. Per-stage fields default None for run-scoped events."""

    run_id: str
    card_id: str
    stage: str | None
    event: str
    ts: str
    harness: str | None = None
    model: str | None = None
    effort: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    duration_s: float | None = None
    gate: dict | None = field(default=None)
    # Capped tail of the stage's returned text, recorded on gate_evaluated
    # (gate-feedback D4); None on older event lines and text-less stages.
    result_text: str | None = None


@dataclass
class RunSummary:
    run_id: str
    outcome: str
    total_cost_usd: float


class RunLedger:
    """Append-only run ledger bound to a repo root."""

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root)
        self.runs_dir = self.repo_root / ".foundry" / "runs"

    def _events_path(self, run_id: str) -> Path:
        return self.runs_dir / run_id / "events.jsonl"

    def append(self, event: RunEvent) -> None:
        path = self._events_path(event.run_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")

    def events(self, run_id: str) -> list[RunEvent]:
        path = self._events_path(run_id)
        if not path.exists():
            return []
        events = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                events.append(RunEvent(**json.loads(line)))
        return events

    def last_boundary(self, run_id: str) -> RunEvent | None:
        boundary = None
        for ev in self.events(run_id):
            if ev.event == "stage_completed":
                boundary = ev
        return boundary

    def list_runs(self) -> list[RunSummary]:
        if not self.runs_dir.exists():
            return []
        summaries = []
        for run_dir in sorted(self.runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            evs = self.events(run_dir.name)
            if not evs:
                continue
            total_cost = sum(ev.cost_usd for ev in evs if ev.cost_usd is not None)
            summaries.append(
                RunSummary(run_id=run_dir.name, outcome=evs[-1].event, total_cost_usd=total_cost)
            )
        return summaries
