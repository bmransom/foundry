"""`foundry run <card-id>` wiring (T7, AC-1.1/1.3/1.8, AC-10.1; T8, AC-1.5/1.6).

Ties the pieces together: Config.load → board resolve → worktree create/reuse →
Driver.run with a real harness adapter (routed via Config.route_for), stage prompts
from compile_stage_prompt, and GateChecks built from config. The only git write is
`git worktree add` — the driver commits nothing to the default branch and pushes
nothing (AC-1.8).

The two StageResult shapes (adapters.parsers vs the driver's local protocol) are
reconciled by an adapter-callable wrapper (`_make_adapter`): it returns the
adapters.parsers.StageResult, which the machine reads by attribute (text,
input_tokens, output_tokens) — no rewrite of machine.py.

T8 adds two entrypoints on top of the same wiring:
- `resume()` reconstructs a halted run from the ledger alone (no Driver config is
  re-derived from anything but the events file) and calls `Driver.resume`, which
  T7/T5 already implemented — this module only wires it.
- `run(..., interactive=True)` switches `_make_adapter`'s callable to launch the
  routed harness's `[interactive]` command instead of the headless one; the
  machine is untouched; it already only calls the adapter for judgment/mixed
  stages and always gates on the returned result the same way.
"""

from __future__ import annotations

import shlex
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from foundry import adapters
from foundry.adapters.parsers import StageResult
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

# Interactive-runner type: (argv, workspace) -> exit status. Injectable so tests
# supply a stub instead of spawning a real interactive session (T8).
InteractiveRunner = Callable[[list, str], int]


class RunNotFoundError(Exception):
    """`--resume` named a run id with no events in the ledger."""


@dataclass(frozen=True)
class _FlaggedRouting:
    """Bakes CLI `--harness/--model/--effort` flags into `Config.route_for` as the
    flag layer (AC-3.1's highest precedence), without changing the driver — which
    calls `config.route_for(stage.name)` with no arguments (`Driver._route`). Duck-
    types as a `Config` for that one call site.
    """

    config: Config
    harness: Optional[str] = None
    model: Optional[str] = None
    effort: Optional[str] = None

    def route_for(self, stage: str) -> Route:
        return self.config.route_for(
            stage, harness=self.harness, model=self.model, effort=self.effort
        )


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


def _spec_dir(spec_cell: str) -> Path:
    """Resolve a board Spec cell to its spec directory.

    The board convention is a directory (`roadmap/specs/<feature>/`, trailing
    slash); a cell that instead names a file resolves to that file's parent dir.
    """
    path = Path(spec_cell.strip())
    return path.parent if path.suffix else path


def _plan_gate(spec_cell: str) -> GateCheck:
    """Plan gate (design D1): PASS when `<spec_dir>/tasks.md` exists in the
    stage's workspace — the plan stage's job is writing that file, so its
    presence is the mechanical proxy for "plan done" until autonomy-level
    approval (also required by the driver's boundary check) is itself gated in
    code. A blank Spec cell always FAILs: there is no spec directory to check.
    """
    cell = (spec_cell or "").strip()
    spec_dir = _spec_dir(cell) if cell else None

    def check(ctx: GateContext) -> GateOutcome:
        if spec_dir is None or ctx.workspace is None:
            return GateOutcome("plan", "FAIL")
        tasks_path = Path(ctx.workspace) / spec_dir / "tasks.md"
        return GateOutcome("plan", "PASS" if tasks_path.is_file() else "FAIL")

    return check


def build_gates(config: Config, spec: str = "") -> dict[str, GateCheck]:
    """Map stage → GateCheck: command gates for build/verify, marker gates for
    spec/review (per stages.py output contracts), a tasks.md existence check for
    plan (design D1). `spec` is the resolved card's board Spec cell. Other
    stages keep the no-op default (PASS) until later waves wire their checks.
    """
    gates: dict[str, GateCheck] = {
        "spec": _marker_gate("spec"),
        "plan": _plan_gate(spec),
        "review": _marker_gate("review"),
        "verify": _commands_gate("gate", config.gate_commands),
    }
    if config.gate_test:
        gates["build"] = _command_gate("tests", config.gate_test)
    return gates


# --- real adapter callable (StageResult reconciliation) -----------------------


def _interactive_subprocess(argv: list, workspace: str) -> int:
    """Default interactive runner: inherit stdio (no capture) so the session
    drives the real terminal (AC-1.5) — never `_run_subprocess`'s captured mode.
    """
    return subprocess.run(argv, cwd=workspace).returncode


def _run_interactive(
    harness: adapters.Adapter,
    route: Optional[Route],
    workspace: Path,
    *,
    run: Optional[InteractiveRunner] = None,
) -> StageResult:
    """Launch the adapter's `[interactive]` command in `workspace`; the session's
    own output is not captured (there is no headless text to parse), so the
    stage's gate evaluates on whatever it checks independent of StageResult.text
    (a command gate) — a marker gate would FAIL on the empty text, which is the
    honest outcome for a stage whose contract needs captured text.
    """
    run = run or _interactive_subprocess
    argv = adapters.expand_argv(
        harness.interactive_command,
        model=route.model if route else None,
        effort=route.effort if route else None,
        workspace=str(workspace),
    )
    returncode = run(argv, str(workspace))
    return StageResult(text="", input_tokens=None, output_tokens=None, exit_status=returncode)


def _make_adapter(
    repo_root: Path,
    card: Card,
    autonomy: AutonomyPolicy,
    *,
    interactive: bool = False,
    interactive_run: Optional[InteractiveRunner] = None,
) -> AdapterCallable:
    """Wrap the harness adapter as a machine-callable.

    Headless (default): compile the stage prompt, run the routed harness
    headlessly, return its StageResult (AC-1.3, AC-10.1). Interactive: skip
    prompt compilation and launch the harness's `[interactive]` command in the
    stage's worktree instead (AC-1.5); the machine calls this callable exactly
    the same way in both cases and gates on its result identically.
    """

    def adapter(stage_name: str, route: Optional[Route], workspace: Path):
        harness = adapters.load(route.harness)
        if interactive:
            return _run_interactive(harness, route, workspace, run=interactive_run)
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
    interactive: bool = False,
    interactive_run: Optional[InteractiveRunner] = None,
    harness: Optional[str] = None,
    model: Optional[str] = None,
    effort: Optional[str] = None,
) -> RunResult:
    """Resolve the card, create/reuse its worktree, and drive the lifecycle.

    `adapter` is injectable (a scripted fake in tests); it defaults to the real
    routed harness adapter, headless unless `interactive=True` (AC-1.5), in which
    case `interactive_run` is the injectable seam for the subprocess call itself
    (defaults to inheriting stdio). The ledger is rooted at the repo.

    `harness`/`model`/`effort` are the CLI flag layer (AC-3.1's highest
    precedence): they override the resolved route for every judgment stage of
    this run, via `_FlaggedRouting` wrapping `config` for the driver's routing
    calls only — `build_gates`/`autonomy` still read the unwrapped `config`.
    """
    repo_root = Path(repo_root)
    config = Config.load(repo_root)
    card = resolve_card(repo_root, card_id)  # BoardError on unknown id
    worktree = ensure_worktree(repo_root, card.id)

    autonomy = AutonomyPolicy(config.autonomy.level, config.autonomy.stop_point)
    ledger = RunLedger(repo_root)
    gates = build_gates(config, spec=card.spec)
    adapter = adapter or _make_adapter(
        repo_root, card, autonomy, interactive=interactive, interactive_run=interactive_run
    )
    routing = _FlaggedRouting(config, harness, model, effort)

    driver = Driver(
        workspace=worktree,
        ledger=ledger,
        card_id=card.id,
        adapter=adapter,
        gates=gates,
        autonomy=autonomy,
        ask=ask,
        config=routing,
        path=path,
        now=now,
    )
    return driver.run()


def resume(
    run_id: str,
    *,
    repo_root: Path | str,
    adapter: Optional[AdapterCallable] = None,
    ask: Optional[Callable[[str], bool]] = None,
    now: Optional[Callable[[], object]] = None,
) -> RunResult:
    """Reconstruct a run from the ledger alone and continue it (AC-1.6).

    The entry path comes from `run_started`'s persisted `stage` field (T7's
    encoding), the card id from any event, and the resume point from
    `RunLedger.last_boundary` (read inside `Driver.resume`, T5). Unknown run id
    raises `RunNotFoundError` listing known run ids; a run already at
    `run_completed` short-circuits with outcome `"already_complete"` and appends
    nothing further to the ledger.
    """
    repo_root = Path(repo_root)
    ledger = RunLedger(repo_root)
    events = ledger.events(run_id)
    if not events:
        known = sorted(s.run_id for s in ledger.list_runs())
        listing = f"known runs: {', '.join(known)}" if known else "no runs recorded"
        raise RunNotFoundError(f"unknown run id '{run_id}'; {listing}")
    if events[-1].event == "run_completed":
        return RunResult(run_id, "already_complete", None, [])

    run_started = next(e for e in events if e.event == "run_started")
    path = run_started.stage
    card_id = events[0].card_id

    config = Config.load(repo_root)
    card = resolve_card(repo_root, card_id)
    worktree = ensure_worktree(repo_root, card.id)

    autonomy = AutonomyPolicy(config.autonomy.level, config.autonomy.stop_point)
    gates = build_gates(config, spec=card.spec)
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
    return driver.resume(run_id)
