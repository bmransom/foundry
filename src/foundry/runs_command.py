"""`foundry runs list` / `foundry runs show <run-id>` (AC-4.3/AC-4.4).

Read-only views over `RunLedger` — no ledger writes, no card/board/config coupling
(the ledger is rooted at the repo, same as `run_command`'s use of it).
"""

from __future__ import annotations

from pathlib import Path

from foundry.ledger import RunLedger

_STAGE_HEADER = ("stage", "harness", "model", "tokens_in", "tokens_out", "cost", "duration_s", "gate")


class RunNotFoundError(Exception):
    """`runs show` named a run id with no events in the ledger."""


def _format_cost(cost: float | None) -> str:
    return "-" if cost is None else f"${cost:.2f}"


def _dash(value) -> str:
    return "-" if value is None else str(value)


def list_lines(repo_root: Path | str) -> list[str]:
    """One line per run: `<run_id> <outcome> <cost>` (AC-4.3)."""
    ledger = RunLedger(repo_root)
    return [
        f"{s.run_id} {s.outcome} {_format_cost(s.total_cost_usd)}"
        for s in ledger.list_runs()
    ]


def _known_ids_listing(ledger: RunLedger) -> str:
    known = sorted(s.run_id for s in ledger.list_runs())
    return f"known runs: {', '.join(known)}" if known else "no runs recorded"


def show_lines(repo_root: Path | str, run_id: str) -> list[str]:
    """The run's stage table (AC-4.4): one row per `stage_completed` event.

    Unknown `run_id` (no events in the ledger) raises `RunNotFoundError` listing
    known run ids.
    """
    ledger = RunLedger(repo_root)
    events = ledger.events(run_id)
    if not events:
        raise RunNotFoundError(f"unknown run id '{run_id}'; {_known_ids_listing(ledger)}")

    rows = [
        (
            _dash(ev.stage),
            _dash(ev.harness),
            _dash(ev.model),
            _dash(ev.input_tokens),
            _dash(ev.output_tokens),
            _format_cost(ev.cost_usd),
            "-" if ev.duration_s is None else f"{ev.duration_s:.1f}",
            (ev.gate or {}).get("outcome", "-"),
        )
        for ev in events
        if ev.event == "stage_completed"
    ]

    widths = [
        max(len(h), *(len(r[i]) for r in rows)) if rows else len(h)
        for i, h in enumerate(_STAGE_HEADER)
    ]

    def fmt(row: tuple) -> str:
        return "  ".join(cell.ljust(w) for cell, w in zip(row, widths))

    lines = [fmt(_STAGE_HEADER), fmt(tuple("-" * w for w in widths))]
    lines += [fmt(r) for r in rows]
    return lines
