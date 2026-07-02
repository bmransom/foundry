"""Stage graph as data (design D1, D8): the eight lifecycle stages, their kinds,
gate slots, stage->rubric map, and the per-path entry map. No orchestration here
— machine.py walks this; prompts.py (T6) loads the rubrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

RETRY_CAP = 3
REVIEW_ROUND_CEILING = 20

# Stage kinds (design D1 table).
MECHANICAL = "mechanical"
JUDGMENT = "judgment"
MIXED = "mixed"


@dataclass(frozen=True)
class OutputContract:
    """A judgment gate's declared last-line marker (D8 output contract, AC-10.2).

    `marker` is the line prefix (before the colon); the gate PASSes when the last
    such line's value equals `pass_value`. None on a stage means a command-shaped
    gate (exit-status, marker-agnostic — build/verify/knowledge/finish/frame/plan).
    """

    marker: str
    pass_value: str


@dataclass(frozen=True)
class Stage:
    name: str
    kind: str
    gate_name: str
    rubrics: tuple = ()
    output_contract: Optional[OutputContract] = None
    # GateCheck callable slot; the driver binds an injected gate into it.
    gate: Optional[Callable] = None


# Ordered eight stages. rubrics name the D8 stage->rubric map targets
# (rubrics/<stage>.md, authored in T6); mechanical stages carry none.
_STAGES = (
    Stage("frame", MECHANICAL, gate_name="frame"),
    Stage("spec", JUDGMENT, gate_name="SPEC_REVIEW", rubrics=("spec",),
          output_contract=OutputContract("SPEC_REVIEW", "CLEAN")),
    Stage("plan", JUDGMENT, gate_name="plan", rubrics=("plan",)),
    Stage("build", JUDGMENT, gate_name="tests", rubrics=("build",)),
    Stage("verify", MECHANICAL, gate_name="gate"),
    Stage("knowledge", MIXED, gate_name="knowledge", rubrics=("knowledge",)),
    Stage("review", JUDGMENT, gate_name="CODE_REVIEW", rubrics=("review",),
          output_contract=OutputContract("CODE_REVIEW", "PASS")),
    Stage("finish", MECHANICAL, gate_name="finish"),
)

STAGES = {s.name: s for s in _STAGES}
STAGE_ORDER = tuple(s.name for s in _STAGES)


@dataclass(frozen=True)
class EntryPath:
    """A run path's entry point + variant flags (design D1)."""

    name: str
    start: str
    light_spec: bool = False
    feature_file_check: bool = True


# Entry map (design D1): feature runs all; bug-fix/refactor enter at build
# (refactor with the feature-file check disabled); enhancement enters at spec
# with the light-spec variant.
ENTRY_PATHS = {
    "feature": EntryPath("feature", start="frame"),
    "bug-fix": EntryPath("bug-fix", start="build"),
    "refactor": EntryPath("refactor", start="build", feature_file_check=False),
    "enhancement": EntryPath("enhancement", start="spec", light_spec=True),
}


def stages_for(path: str) -> list[Stage]:
    if path not in ENTRY_PATHS:
        raise ValueError(
            f"unknown path '{path}'; valid: {', '.join(ENTRY_PATHS)}"
        )
    start = ENTRY_PATHS[path].start
    start_idx = STAGE_ORDER.index(start)
    return [STAGES[name] for name in STAGE_ORDER[start_idx:]]
