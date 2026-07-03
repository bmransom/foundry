"""The driver: a deterministic state machine over the v1 lifecycle (design D1).

Gates are preconditions evaluated by code — a stage's gate must pass before the
next stage is entered (AC-1.2); RETRY_CAP consecutive failures halt the run
(AC-1.4); review FAIL loops back to build, and REVIEW_ROUND_CEILING rounds halt.
Judgment/mixed stages call an injected adapter; mechanical stages run their gate
only. Stage hooks run at boundaries (AC-1.9). Pure orchestration — no git,
worktree, or board work (that is T7); the driver operates on an injected
workspace and injected GateChecks.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Optional, Protocol

from foundry.adapters.parsers import StageResult
from foundry.config import Config, Route
from foundry.ledger import RunEvent, RunLedger, compute_cost, new_run_id
from foundry.driver.stages import (
    ENTRY_PATHS,
    JUDGMENT,
    MIXED,
    RETRY_CAP,
    REVIEW_ROUND_CEILING,
    Stage,
    stages_for,
)

ALLOWED_LEVELS = frozenset({"supervised", "guided", "autonomous"})
ALLOWED_STOP_POINTS = frozenset({"feature", "card", "epic", "roadmap"})


class AutonomyError(ValueError):
    """An autonomy level or stop-point outside the allowed set."""


@dataclass(frozen=True)
class AutonomyPolicy:
    """Autonomy level + stop-point, validated (config.py defers this to the driver)."""

    level: str = "guided"
    # stop_point is validated but not yet consumed: a single run() never chains
    # past one card; it takes effect once multi-card chaining lands.
    stop_point: str = "card"

    def __post_init__(self):
        if self.level not in ALLOWED_LEVELS:
            raise AutonomyError(
                f"autonomy level '{self.level}' not in {sorted(ALLOWED_LEVELS)}"
            )
        if self.stop_point not in ALLOWED_STOP_POINTS:
            raise AutonomyError(
                f"stop_point '{self.stop_point}' not in {sorted(ALLOWED_STOP_POINTS)}"
            )


# --- adapter / gate protocols ---------------------------------------------
# StageResult is `foundry.adapters.parsers.StageResult` (design D2) — one shape,
# not two; the driver only reads it by attribute (text, input_tokens, output_tokens).


# Tail caps: bound what a failed gate feeds a retry prompt and what a stage's
# returned text costs the ledger (gate-feedback design D1/D4).
FEEDBACK_DETAIL_CAP = 4000
RESULT_TEXT_CAP = 4000


def _tail(text: str, cap: int) -> str:
    return text if len(text) <= cap else text[-cap:]


@dataclass(frozen=True)
class GateOutcome:
    name: str
    outcome: str  # "PASS" | "FAIL"
    detail: str = ""  # evidence on FAIL — capped output tail or explanation (D2)


@dataclass(frozen=True)
class GateFeedback:
    """A failed gate's evidence, fed into the retried stage's prompt (design D1).

    `attempt` is the 1-based number of the attempt that FAILED. One slot, latest
    evidence wins: a fresh FAIL replaces prior feedback, never accumulates.
    """

    gate: str
    attempt: int
    detail: str


@dataclass(frozen=True)
class GateContext:
    workspace: Optional[Path]
    result: Optional[StageResult]


class Adapter(Protocol):
    def __call__(
        self,
        stage: str,
        route: Optional[Route],
        workspace: Path,
        feedback: Optional[GateFeedback] = None,
    ) -> StageResult:
        ...


class GateCheck(Protocol):
    def __call__(self, ctx: GateContext) -> GateOutcome:
        ...


@dataclass
class RunResult:
    run_id: str
    outcome: str  # "completed" | "halted" | "stopped" | "already_complete" (T8, run_command.resume)
    halted_gate: Optional[str] = None
    stages_started: list = field(default_factory=list)


# --- gate factories (used by T7 to build real gates; unit-tested here) --------


def command_gate(name: str, argv: list) -> GateCheck:
    """A command-shaped gate: PASS on exit 0, marker-agnostic (design D1).

    Output is captured for the FAIL detail (stdout+stderr merged, capped tail;
    AC-2.1) and written through to stdout, so the driver's log keeps showing
    gate output.
    """

    def check(ctx: GateContext) -> GateOutcome:
        proc = subprocess.run(
            argv,
            cwd=str(ctx.workspace) if ctx.workspace else None,
            capture_output=True,
        )
        raw = (proc.stdout or b"") + (proc.stderr or b"")
        if raw:
            # Write through as bytes: the driver's stdout codec never re-encodes
            # untrusted gate output, so it can never crash the run.
            buffer = getattr(sys.stdout, "buffer", None)
            if buffer is not None:
                buffer.write(raw)
                sys.stdout.flush()
            else:  # a replaced stdout (e.g. capture layers) — decode lossily
                print(raw.decode("utf-8", errors="replace"), end="", flush=True)
        if proc.returncode == 0:
            return GateOutcome(name, "PASS")
        output = raw.decode("utf-8", errors="replace")
        return GateOutcome(name, "FAIL", detail=_tail(output, FEEDBACK_DETAIL_CAP))

    return check


def marker_gate(name: str, marker: str, pass_value: str) -> GateCheck:
    """An output-contract gate: parse the declared last-line marker (AC-10.2)."""

    prefix = f"{marker}:"

    def check(ctx: GateContext) -> GateOutcome:
        text = ctx.result.text if ctx.result else ""
        value = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(prefix):
                value = line[len(prefix):].strip()
        if value == pass_value:
            return GateOutcome(name, "PASS")
        detail = (
            f"no '{marker}:' line in the stage output"
            if value is None
            else f"last '{marker}:' value was '{value}', expected '{pass_value}'"
        )
        return GateOutcome(name, "FAIL", detail=detail)

    return check


class Driver:
    """Walks the stage graph for one card, recording the run ledger."""

    def __init__(
        self,
        *,
        workspace: Path | str,
        ledger: RunLedger,
        card_id: str,
        adapter: Adapter,
        gates: Mapping[str, GateCheck],
        autonomy: AutonomyPolicy = AutonomyPolicy(),
        ask: Optional[Callable[[str], bool]] = None,
        config: Optional[Config] = None,
        path: str = "feature",
        now: Optional[Callable[[], datetime]] = None,
    ):
        if not isinstance(autonomy, AutonomyPolicy):
            autonomy = AutonomyPolicy(autonomy.level, autonomy.stop_point)
        self.workspace = Path(workspace)
        self._ledger = ledger
        self.card_id = card_id
        self._adapter = adapter
        self._autonomy = autonomy
        self._ask_cb = ask
        self._config = config
        self._path = path
        self._now = now or (lambda: datetime.now(timezone.utc))
        # Bind injected GateChecks into each stage's gate slot (design D1).
        self._order = [
            replace(s, gate=gates.get(s.name, s.gate)) for s in stages_for(path)
        ]
        self._build_idx = self._index_of("build")
        # per-path variant flags (data for T7; not gated in T5)
        self.light_spec = ENTRY_PATHS[path].light_spec
        self.feature_file_check = ENTRY_PATHS[path].feature_file_check

    # --- public API -----------------------------------------------------------

    def run(self) -> RunResult:
        run_id = new_run_id(self._now())
        self._started: list = []
        # Persist the entry path on run_started's stage field so resume (T8) can
        # reconstruct the same machine without reading Driver config.
        self._append(self._event(run_id, "run_started", stage=self._path))
        return self._walk(run_id, start_idx=0)

    def resume(self, run_id: str) -> RunResult:
        """Resume from the last recorded stage boundary (AC-1.6)."""
        self._started = []
        boundary = self._ledger.last_boundary(run_id)
        self._append(self._event(run_id, "run_resumed"))
        if boundary is None or boundary.stage is None:
            start_idx = 0
        else:
            start_idx = self._index_of(boundary.stage) + 1
        return self._walk(run_id, start_idx=start_idx)

    # --- the walk -------------------------------------------------------------

    def _walk(self, run_id: str, start_idx: int) -> RunResult:
        idx = start_idx
        review_rounds = 0
        carry: Optional[GateFeedback] = None  # review findings for build re-entry (D3)
        while idx < len(self._order):
            stage = self._order[idx]
            route = self._route(stage)

            # Pre hook: a non-zero pre hook blocks stage entry (AC-1.9).
            pre = self._run_hook(run_id, stage, "pre")
            if pre not in (None, 0):
                name = f"{stage.name}.pre hook"
                self._halt(run_id, stage, name)
                return RunResult(run_id, "halted", name, self._started)

            self._append(self._event(run_id, "stage_started", stage=stage, route=route))
            self._started.append(stage.name)
            self._stage_start = time.monotonic()

            if stage.name == "review":
                outcome, result = self._run_body(run_id, stage, route, feedback=carry)
                carry = None
                if outcome.outcome == "PASS":
                    self._complete(run_id, stage, route, result, outcome)
                else:
                    review_rounds += 1
                    if review_rounds >= REVIEW_ROUND_CEILING:
                        self._halt(run_id, stage, outcome.name)
                        return RunResult(run_id, "halted", outcome.name, self._started)
                    # The findings live in the review's returned text; the gate's
                    # own detail (marker verdict / failed hook) leads so a hook
                    # FAIL never feeds evidence that contradicts the failure (D3).
                    parts = [p for p in (outcome.detail, result.text if result else "") if p]
                    carry = GateFeedback(
                        outcome.name,
                        review_rounds,
                        _tail("\n".join(parts), FEEDBACK_DETAIL_CAP),
                    )
                    idx = self._build_idx  # loop back to build
                    continue
            else:
                halt = self._run_with_retry(run_id, stage, route, feedback=carry)
                carry = None
                if halt is not None:
                    return halt

            # Boundary: honor autonomy (AC-1.7).
            if idx + 1 < len(self._order) and self._should_ask(stage):
                if not self._ask(stage.name):
                    self._append(self._event(run_id, "run_completed"))
                    return RunResult(run_id, "stopped", None, self._started)
            idx += 1

        self._append(self._event(run_id, "run_completed"))
        return RunResult(run_id, "completed", None, self._started)

    def _run_with_retry(self, run_id, stage, route, feedback=None) -> Optional[RunResult]:
        """Run a non-review stage; None on PASS, a halted RunResult on RETRY_CAP.

        Each FAIL becomes the next attempt's GateFeedback (AC-1.1) — the retry is
        a correction, not a blind replay of the same prompt.
        """
        attempts = 0
        while True:
            attempts += 1
            outcome, result = self._run_body(run_id, stage, route, feedback=feedback)
            if outcome.outcome == "PASS":
                self._complete(run_id, stage, route, result, outcome)
                return None
            if attempts >= RETRY_CAP:
                self._halt(run_id, stage, outcome.name)
                return RunResult(run_id, "halted", outcome.name, self._started)
            feedback = GateFeedback(outcome.name, attempts, outcome.detail)

    def _run_body(
        self, run_id, stage, route, feedback=None
    ) -> tuple[GateOutcome, Optional[StageResult]]:
        """Adapter (judgment/mixed) + post hook + gate, emitting gate_evaluated."""
        result = None
        if stage.kind in (JUDGMENT, MIXED):
            result = self._adapter(stage.name, route, self.workspace, feedback=feedback)
        post = self._run_hook(run_id, stage, "post")
        if post not in (None, 0):
            # Post hook fails the gate — with evidence, so the retry isn't blind.
            outcome = GateOutcome(
                stage.gate_name, "FAIL",
                detail=f"{stage.name}.post hook exited {post}",
            )
        elif stage.gate is None:
            outcome = GateOutcome(stage.gate_name, "PASS")
        else:
            outcome = stage.gate(GateContext(self.workspace, result))
        self._append(
            self._event(
                run_id, "gate_evaluated", stage=stage, route=route, result=result,
                gate={"name": outcome.name, "outcome": outcome.outcome},
                result_text=(
                    _tail(result.text, RESULT_TEXT_CAP)
                    if result is not None and result.text
                    else None
                ),
            )
        )
        return outcome, result

    # --- hooks ----------------------------------------------------------------

    def _run_hook(self, run_id, stage, phase) -> Optional[int]:
        """Run .foundry/hooks/<stage>.<phase>.sh if executable; else skip (None).

        Executable bit is the opt-in; runs with cwd = workspace; emits
        hook_evaluated (AC-1.9).
        """
        path = self.workspace / ".foundry" / "hooks" / f"{stage.name}.{phase}.sh"
        if not path.is_file() or not os.access(path, os.X_OK):
            return None
        proc = subprocess.run([str(path)], cwd=str(self.workspace))
        outcome = "PASS" if proc.returncode == 0 else "FAIL"
        self._append(
            self._event(
                run_id, "hook_evaluated", stage=stage,
                gate={"name": f"{stage.name}.{phase} hook", "outcome": outcome},
            )
        )
        return proc.returncode

    # --- autonomy -------------------------------------------------------------

    def _should_ask(self, stage) -> bool:
        level = self._autonomy.level
        if level == "autonomous":
            return False
        if level == "supervised":
            return True
        return stage.name == "plan"  # guided: decision point = plan approval

    def _ask(self, stage_name) -> bool:
        if self._ask_cb is None:
            return True
        return bool(self._ask_cb(stage_name))

    # --- routing / events -----------------------------------------------------

    def _route(self, stage) -> Optional[Route]:
        if self._config is None:
            return Route(None, None, None)
        return self._config.route_for(stage.name)

    def _index_of(self, name) -> int:
        for i, s in enumerate(self._order):
            if s.name == name:
                return i
        return -1

    def _complete(self, run_id, stage, route, result, outcome):
        duration = time.monotonic() - getattr(self, "_stage_start", time.monotonic())
        self._append(
            self._event(
                run_id, "stage_completed", stage=stage, route=route, result=result,
                gate={"name": outcome.name, "outcome": outcome.outcome},
                duration_s=duration,
            )
        )

    def _halt(self, run_id, stage, gate_name):
        self._append(
            self._event(
                run_id, "run_halted", stage=stage,
                gate={"name": gate_name, "outcome": "FAIL"},
            )
        )

    def _event(self, run_id, event, *, stage=None, route=None, result=None,
               gate=None, duration_s=None, result_text=None) -> RunEvent:
        harness = route.harness if route else None
        model = route.model if route else None
        effort = route.effort if route else None
        in_tok = result.input_tokens if result else None
        out_tok = result.output_tokens if result else None
        return RunEvent(
            run_id=run_id,
            card_id=self.card_id,
            stage=stage.name if isinstance(stage, Stage) else stage,
            event=event,
            ts=self._ts(),
            harness=harness,
            model=model,
            effort=effort,
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=compute_cost(model, in_tok, out_tok),
            duration_s=duration_s,
            gate=gate,
            result_text=result_text,
        )

    def _append(self, event: RunEvent):
        self._ledger.append(event)

    def _ts(self) -> str:
        return self._now().strftime("%Y-%m-%dT%H:%M:%SZ")
