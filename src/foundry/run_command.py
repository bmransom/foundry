"""`foundry run <card-id>` wiring (T7, AC-1.1/1.3/1.8, AC-10.1).

Ties the pieces together: Config.load → board resolve → worktree create/reuse →
Driver.run with a real harness adapter (routed via Config.route_for), stage prompts
from compile_stage_prompt, and GateChecks built from config. The only git write is
`git worktree add` — the driver commits nothing to the default branch and pushes
nothing (AC-1.8).

The two StageResult shapes (adapters.parsers vs the driver's local protocol) are
reconciled by an adapter-callable wrapper (`_make_adapter`): it returns the
adapters.parsers.StageResult, which the machine reads by attribute (text,
input_tokens, output_tokens) — no rewrite of machine.py.
"""

from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

from foundry import adapters
from foundry.board import Card, resolve_card
from foundry.config import Config, Route
from foundry.driver.machine import (
    AutonomyPolicy,
    Driver,
    GateContext,
    GateCheck,
    GateOutcome,
    RunResult,
    command_gate,
    marker_gate,
)
from foundry.driver.prompts import CardContext, compile_stage_prompt
from foundry.driver.stages import STAGES
from foundry.ledger import RunLedger

# Adapter-callable type: (stage_name, route, workspace) -> StageResult-shaped object.
AdapterCallable = Callable[[str, Optional[Route], Path], object]


# --- worktree (the only git write; AC-1.8 bounds it) --------------------------


def default_branch(repo_root: Path) -> str:
    """Default branch from origin/HEAD, falling back to `main`."""
    proc = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def _ref_exists(repo_root: Path, ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=str(repo_root), capture_output=True,
    ).returncode == 0


def ensure_worktree(repo_root: Path, card_id: str) -> Path:
    """Create `wt/<id>` on branch `card/<id>` off the default branch, or reuse it.

    Prefers `origin/<default>` as the base (the convention), falling back to the
    local default branch when there is no origin (a local-only fixture repo).
    """
    worktree = repo_root / "wt" / card_id
    if worktree.exists():
        return worktree
    branch = f"card/{card_id}"
    if _ref_exists(repo_root, branch):
        subprocess.run(
            ["git", "worktree", "add", str(worktree), branch],
            cwd=str(repo_root), check=True, capture_output=True, text=True,
        )
        return worktree
    default = default_branch(repo_root)
    base = f"origin/{default}" if _ref_exists(repo_root, f"origin/{default}") else default
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree), base],
        cwd=str(repo_root), check=True, capture_output=True, text=True,
    )
    return worktree


# --- gates from config (design D1) --------------------------------------------


def _command_gate(name: str, command: str) -> GateCheck:
    return command_gate(name, shlex.split(command))


def _commands_gate(name: str, commands: list[str]) -> GateCheck:
    """Verify's gate: every `[gate].commands` entry must exit 0 (design D1)."""
    checks = [_command_gate(name, c) for c in commands]

    def check(ctx: GateContext) -> GateOutcome:
        for chk in checks:
            outcome = chk(ctx)
            if outcome.outcome != "PASS":
                return outcome
        return GateOutcome(name, "PASS")

    return check


def _marker_gate(stage_name: str) -> GateCheck:
    stage = STAGES[stage_name]
    contract = stage.output_contract
    return marker_gate(stage.gate_name, contract.marker, contract.pass_value)


def build_gates(config: Config) -> dict[str, GateCheck]:
    """Map stage → GateCheck: command gates for build/verify, marker gates for
    spec/review (per stages.py output contracts). Other stages keep the no-op
    default (PASS) until later waves wire their checks.
    """
    gates: dict[str, GateCheck] = {
        "spec": _marker_gate("spec"),
        "review": _marker_gate("review"),
        "verify": _commands_gate("gate", config.gate_commands),
    }
    if config.gate_test:
        gates["build"] = _command_gate("tests", config.gate_test)
    return gates


# --- real adapter callable (StageResult reconciliation) -----------------------


def _make_adapter(repo_root: Path, card: Card, autonomy: AutonomyPolicy) -> AdapterCallable:
    """Wrap the harness adapter as a machine-callable: compile the stage prompt,
    run the routed harness headlessly, return its StageResult (AC-1.3, AC-10.1).
    """

    def adapter(stage_name: str, route: Optional[Route], workspace: Path):
        stage = STAGES[stage_name]
        card_context = CardContext(
            card_id=card.id,
            spec_paths=(card.spec,),
            worktree=str(workspace),
            autonomy=autonomy.level,
        )
        prompt = compile_stage_prompt(stage, card_context)
        tmp_dir = Path(workspace) / ".foundry" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", dir=str(tmp_dir), delete=False, encoding="utf-8"
        ) as fh:
            fh.write(prompt)
            prompt_file = fh.name
        harness = adapters.load(route.harness)
        return adapters.headless(harness, prompt_file, route, str(workspace))

    return adapter


# --- entrypoint ---------------------------------------------------------------


def run(
    card_id: str,
    *,
    repo_root: Path | str,
    path: str = "feature",
    adapter: Optional[AdapterCallable] = None,
    ask: Optional[Callable[[str], bool]] = None,
    now: Optional[Callable[[], object]] = None,
) -> RunResult:
    """Resolve the card, create/reuse its worktree, and drive the lifecycle.

    `adapter` is injectable (a scripted fake in tests); it defaults to the real
    routed harness adapter. The ledger is rooted at the repo.
    """
    repo_root = Path(repo_root)
    config = Config.load(repo_root)
    card = resolve_card(repo_root, card_id)  # BoardError on unknown id
    worktree = ensure_worktree(repo_root, card.id)

    autonomy = AutonomyPolicy(config.autonomy.level, config.autonomy.stop_point)
    ledger = RunLedger(repo_root)
    gates = build_gates(config)
    adapter = adapter or _make_adapter(repo_root, card, autonomy)

    driver = Driver(
        workspace=worktree,
        ledger=ledger,
        card_id=card.id,
        adapter=adapter,
        gates=gates,
        autonomy=autonomy,
        ask=ask,
        config=config,
        path=path,
        now=now,
    )
    return driver.run()
