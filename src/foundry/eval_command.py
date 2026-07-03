"""`foundry eval --matrix <spec>` — the eval matrix runner (T17, US-8, AC-8.1/8.2).

Grades a generated gate by **discrimination**: a fixture pair is a seeded twin (a repo
with a deliberate defect, expected verdict FAIL) and its clean twin (expected PASS). A
cell (harness×model[×effort]) discriminates on a pair iff the seeded twin FAILs *and* the
clean twin PASSes — one without the other is a non-discriminating cell (AGENTS.md: never
let a gate grade itself). The stage under test is `review`, run through the driver's
headless path (real adapter) over each twin's diff; the review marker gate decides each
twin's verdict, so grading measures the gate under test, not a stand-in.

Stdlib only. The adapter is injectable so tests grade with fakes and never call an LLM.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from foundry import adapters
from foundry.adapters.parsers import StageResult
from foundry.driver.machine import GateContext, marker_gate
from foundry.driver.prompts import CardContext, compile_stage_prompt
from foundry.driver.stages import STAGES
from foundry.ledger import compute_cost
from foundry.config import Route

# Adapter callable, the driver's shape: (stage, route, workspace, feedback=None)
# -> StageResult (feedback: gate-feedback AC-1.1; the matrix always passes None).
Adapter = Callable[..., StageResult]

# The review stage's output-contract gate — the gate under test (AC-10.2).
_REVIEW_GATE = marker_gate("review", "CODE_REVIEW", "PASS")


class EvalError(Exception):
    """A malformed matrix spec, or no fixture pair matched."""


# --- matrix spec --------------------------------------------------------------


@dataclass(frozen=True)
class Cell:
    harness: str
    model: str
    effort: Optional[str] = None

    @property
    def label(self) -> str:
        base = f"{self.harness}:{self.model}"
        return f"{base}:{self.effort}" if self.effort else base

    def route(self) -> Route:
        return Route(self.harness, self.model, self.effort)


def parse_matrix(spec: str) -> list[Cell]:
    """Parse `harness:model[:effort],…` into cells; a malformed cell raises EvalError."""
    cells = []
    for raw in spec.split(","):
        cell = raw.strip()
        if not cell:
            raise EvalError(f"empty cell in matrix spec {spec!r}")
        parts = cell.split(":")
        if len(parts) not in (2, 3) or not all(p.strip() for p in parts):
            raise EvalError(
                f"bad cell {cell!r}: expected harness:model[:effort] with non-empty fields"
            )
        harness, model = parts[0].strip(), parts[1].strip()
        effort = parts[2].strip() if len(parts) == 3 else None
        cells.append(Cell(harness, model, effort))
    return cells


# --- fixture discovery --------------------------------------------------------


@dataclass(frozen=True)
class FixturePair:
    name: str
    path: Path
    stage: str
    seeded: Path
    clean: Path
    seeded_expected: str
    clean_expected: str


def _load_expected(twin: Path) -> tuple[str, str]:
    expected = json.loads((twin / "expected.json").read_text())
    return expected["stage"], expected["verdict"]


def discover_fixtures(matrix_root: Path | str, name: Optional[str] = None) -> list[FixturePair]:
    """Discover fixture pairs under `matrix_root`: a dir with `seeded/` and `clean/`
    twins, each carrying `expected.json`. `name` filters to one pair. EvalError when
    nothing matches (a filter that hits nothing, or an empty matrix root).
    """
    root = Path(matrix_root)
    pairs = []
    for child in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        if name is not None and child.name != name:
            continue
        seeded, clean = child / "seeded", child / "clean"
        if not (seeded / "expected.json").is_file() or not (clean / "expected.json").is_file():
            continue
        stage, seeded_verdict = _load_expected(seeded)
        _, clean_verdict = _load_expected(clean)
        pairs.append(
            FixturePair(child.name, child, stage, seeded, clean, seeded_verdict, clean_verdict)
        )
    if not pairs:
        where = f" matching '{name}'" if name else ""
        raise EvalError(f"no fixture pairs{where} under {root}")
    return pairs


# --- grading ------------------------------------------------------------------


def is_discriminating(seeded_verdict: str, clean_verdict: str) -> bool:
    """A cell discriminates iff the seeded twin FAILs and the clean twin PASSes (AC-8.2)."""
    return seeded_verdict == "FAIL" and clean_verdict == "PASS"


@dataclass(frozen=True)
class Row:
    cell: str
    fixture: str
    seeded_verdict: str
    clean_verdict: str
    discriminating: bool
    cost_usd: Optional[float]
    blocked: bool = False
    error: Optional[str] = None


def _verdict(result: StageResult) -> str:
    """The review gate's PASS/FAIL verdict over one twin's harness output (AC-10.2)."""
    return _REVIEW_GATE(GateContext(None, result)).outcome


def _run_twin(adapter: Adapter, cell: Cell, twin: Path, stage: str) -> tuple[str, Optional[float]]:
    result = adapter(stage, cell.route(), twin)
    cost = compute_cost(cell.model, result.input_tokens, result.output_tokens)
    return _verdict(result), cost


def evaluate_matrix(
    cells: list[Cell],
    fixtures_root: Path | str,
    *,
    fixture: Optional[str] = None,
    adapter: Optional[Adapter] = None,
    pairs: Optional[list[FixturePair]] = None,
) -> list[Row]:
    """Run every cell × pair through `adapter`, grading discrimination and cost.

    `pairs` lets a caller that already discovered fixtures (e.g. `run_matrix`) pass
    them through instead of triggering a second `discover_fixtures` pass.
    """
    adapter = adapter or headless_review_adapter
    if pairs is None:
        pairs = discover_fixtures(fixtures_root, fixture)
    rows = []
    for cell in cells:
        for pair in pairs:
            try:
                seeded_verdict, seeded_cost = _run_twin(adapter, cell, pair.seeded, pair.stage)
                clean_verdict, clean_cost = _run_twin(adapter, cell, pair.clean, pair.stage)
            except Exception as exc:  # a blocked cell (auth/rate limit): report, never fake
                rows.append(
                    Row(cell.label, pair.name, "ERR", "ERR", False, None,
                        blocked=True, error=str(exc))
                )
                continue
            cost = _sum_cost(seeded_cost, clean_cost)
            rows.append(
                Row(
                    cell.label, pair.name, seeded_verdict, clean_verdict,
                    is_discriminating(seeded_verdict, clean_verdict), cost,
                )
            )
    return rows


def _sum_cost(*costs: Optional[float]) -> Optional[float]:
    known = [c for c in costs if c is not None]
    return sum(known) if known else None


# --- the real headless adapter (review over a twin's diff) --------------------

_DIFF_INSTRUCTION = (
    "\n\n---\n\n## Change under review\n\n"
    "This repository has one staged change against HEAD. Run `git diff HEAD` to read "
    "it, review that diff against the spec under `roadmap/specs/`, and emit your verdict "
    "per the output contract — a final `CODE_REVIEW: PASS` or `CODE_REVIEW: FAIL` line.\n"
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=eval@foundry", "-c", "user.name=eval", *args],
        cwd=str(repo), check=True, capture_output=True, text=True,
    )


def _materialize_twin(twin: Path) -> Path:
    """Build a throwaway git repo: commit `base/`, then replace the working tree with
    `head/` and stage it, so `git diff HEAD` is the change to review. Never touches a
    real repo (a fresh temp dir), so the eval-sandbox git-config class cannot apply.
    """
    tmp = Path(tempfile.mkdtemp(prefix="foundry-eval-matrix-"))
    repo = tmp / "repo"
    shutil.copytree(twin / "base", repo)
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "baseline")
    for item in repo.iterdir():
        if item.name == ".git":
            continue
        shutil.rmtree(item) if item.is_dir() else item.unlink()
    shutil.copytree(twin / "head", repo, dirs_exist_ok=True)
    _git(repo, "add", "-A")
    return repo


def headless_review_adapter(
    stage: str, route: Route, workspace: Path, feedback=None
) -> StageResult:
    """Run the review stage headlessly over a twin's diff (the driver's headless path).

    `workspace` is a fixture twin dir (base/ + head/); it is materialized into a temp
    git repo, the review rubric compiled with the diff instruction, and the routed
    harness run headlessly. The temp repo is removed afterward.
    """
    twin = Path(workspace)
    repo = _materialize_twin(twin)
    try:
        card_context = CardContext(
            card_id=f"eval-{twin.parent.name}-{twin.name}",
            spec_paths=("roadmap/specs/",),
            worktree=str(repo),
            autonomy="autonomous",
        )
        prompt = compile_stage_prompt(STAGES[stage], card_context) + _DIFF_INSTRUCTION
        prompt_file = repo / ".foundry-eval-prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        harness = adapters.load(route.harness)
        return adapters.headless(harness, str(prompt_file), route, str(repo))
    finally:
        shutil.rmtree(repo.parent, ignore_errors=True)


# --- rendering ----------------------------------------------------------------


def _fmt_cost(cost: Optional[float]) -> str:
    return "n/a" if cost is None else f"${cost:.4f}"


def _render_table(rows: list[Row]) -> list[str]:
    header = ("cell", "fixture", "seeded", "clean", "discriminating", "cost")
    table = [header] + [
        (r.cell, r.fixture, r.seeded_verdict, r.clean_verdict,
         "yes" if r.discriminating else "no", _fmt_cost(r.cost_usd))
        for r in rows
    ]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    lines = ["  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in table]
    for r in rows:
        if r.blocked:
            lines.append(f"  blocked: {r.cell} × {r.fixture}: {r.error}")
    return lines


def run_matrix(
    *,
    matrix: str,
    fixtures_root: Optional[Path | str] = None,
    repo_root: Optional[Path | str] = None,
    fixture: Optional[str] = None,
    dry_run: bool = False,
    adapter: Optional[Adapter] = None,
) -> tuple[bool, list[str]]:
    """Parse the matrix, discover fixtures, and either list (dry-run) or run + grade.

    Returns (ok, lines). ok is False on any non-discriminating or blocked cell.
    `fixtures_root` defaults to `<repo_root>/evals/fixtures/matrix`.
    """
    if fixtures_root is None:
        fixtures_root = Path(repo_root or ".") / "evals" / "fixtures" / "matrix"
    cells = parse_matrix(matrix)
    pairs = discover_fixtures(fixtures_root, fixture)

    if dry_run:
        lines = [f"{cell.label}  {pair.name}" for cell in cells for pair in pairs]
        lines.append(f"eval: dry-run ({len(cells)} cells × {len(pairs)} fixtures)")
        return True, lines

    rows = evaluate_matrix(cells, fixtures_root, adapter=adapter, pairs=pairs)
    discriminating = sum(1 for r in rows if r.discriminating)
    ok = discriminating == len(rows)
    lines = _render_table(rows)
    verdict = "OK" if ok else "FAIL"
    lines.append(f"eval: {verdict} ({discriminating}/{len(rows)} cells discriminating)")
    return ok, lines
