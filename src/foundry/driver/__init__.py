"""Driver package: the deterministic lifecycle state machine (design D1)."""

from foundry.driver.machine import (
    Adapter,
    AutonomyError,
    AutonomyPolicy,
    Driver,
    GateCheck,
    GateContext,
    GateOutcome,
    RunResult,
    StageResult,
    command_gate,
    marker_gate,
)
from foundry.driver.stages import (
    ENTRY_PATHS,
    REVIEW_ROUND_CEILING,
    RETRY_CAP,
    STAGE_ORDER,
    STAGES,
    EntryPath,
    OutputContract,
    Stage,
    stages_for,
)

__all__ = [
    "Adapter",
    "AutonomyError",
    "AutonomyPolicy",
    "Driver",
    "GateCheck",
    "GateContext",
    "GateOutcome",
    "RunResult",
    "StageResult",
    "command_gate",
    "marker_gate",
    "ENTRY_PATHS",
    "REVIEW_ROUND_CEILING",
    "RETRY_CAP",
    "STAGE_ORDER",
    "STAGES",
    "EntryPath",
    "OutputContract",
    "Stage",
    "stages_for",
]
