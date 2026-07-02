"""Tests for foundry.eval_command (T17): the eval matrix runner (US-8, AC-8.1/8.2).

Everything here is exercised with injected fake adapters — no live LLM calls. The
one live matrix run is the T17 gate, pasted into the PR, never run in pytest.

The fake adapters return the review stage's declared marker (`CODE_REVIEW: PASS|FAIL`)
so grading runs through the *real* review gate — discrimination is measured against the
gate under test, not a stand-in (AGENTS.md: never let a gate grade itself).
"""

import json
from pathlib import Path

import pytest

from foundry.adapters.parsers import StageResult
from foundry.eval_command import (
    Cell,
    EvalError,
    discover_fixtures,
    evaluate_matrix,
    is_discriminating,
    parse_matrix,
    run_matrix,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REAL_MATRIX = REPO_ROOT / "evals" / "fixtures" / "matrix"


# --- fake adapters -------------------------------------------------------------


class FakeReviewAdapter:
    """Returns the review marker keyed by the twin dir name (seeded|clean)."""

    def __init__(self, verdicts, input_tokens=1000, output_tokens=200):
        self.verdicts = verdicts  # {"seeded": "FAIL", "clean": "PASS"}
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.calls = []

    def __call__(self, stage, route, workspace):
        twin = Path(workspace).name
        self.calls.append((stage, route.harness, route.model, twin))
        verdict = self.verdicts[twin]
        return StageResult(
            text=f"findings...\nCODE_REVIEW: {verdict}",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            exit_status=0,
        )


class ExplodingAdapter:
    """Raises on every call — stands in for auth/rate-limit failure (a blocked cell)."""

    def __call__(self, stage, route, workspace):
        raise RuntimeError("simulated auth failure")


# --- fixture builders ----------------------------------------------------------


def _make_pair(root, name, *, stage="review", seeded="FAIL", clean="PASS"):
    pair = root / name
    for twin, verdict in (("seeded", seeded), ("clean", clean)):
        d = pair / twin
        d.mkdir(parents=True)
        (d / "expected.json").write_text(json.dumps({"stage": stage, "verdict": verdict}))
    return pair


# --- matrix-spec parsing -------------------------------------------------------


def test_parse_matrix_two_and_three_field_cells():
    cells = parse_matrix("claude-code:claude-sonnet-5,codex:gpt-5.5:high")
    assert cells == [
        Cell("claude-code", "claude-sonnet-5", None),
        Cell("codex", "gpt-5.5", "high"),
    ]


def test_parse_matrix_label_round_trips():
    (cell,) = parse_matrix("codex:gpt-5.5:high")
    assert cell.label == "codex:gpt-5.5:high"


@pytest.mark.parametrize("bad", ["", "claude-code", "a:b:c:d", "claude-code:", ":m", "a::"])
def test_parse_matrix_rejects_bad_cell(bad):
    with pytest.raises(EvalError):
        parse_matrix(bad)


# --- fixture discovery ---------------------------------------------------------


def test_discover_fixtures_finds_pairs(tmp_path):
    _make_pair(tmp_path, "b-pair")
    _make_pair(tmp_path, "a-pair")
    pairs = discover_fixtures(tmp_path)
    assert [p.name for p in pairs] == ["a-pair", "b-pair"]  # sorted
    assert pairs[0].stage == "review"
    assert pairs[0].seeded_expected == "FAIL"
    assert pairs[0].clean_expected == "PASS"


def test_discover_fixtures_filter(tmp_path):
    _make_pair(tmp_path, "wanted")
    _make_pair(tmp_path, "other")
    pairs = discover_fixtures(tmp_path, name="wanted")
    assert [p.name for p in pairs] == ["wanted"]


def test_discover_fixtures_unknown_filter_errors(tmp_path):
    _make_pair(tmp_path, "wanted")
    with pytest.raises(EvalError):
        discover_fixtures(tmp_path, name="nope")


def test_discover_fixtures_none_found_errors(tmp_path):
    with pytest.raises(EvalError):
        discover_fixtures(tmp_path)


def test_real_review_defect_fixture_is_wellformed():
    pairs = discover_fixtures(REAL_MATRIX, name="review-defect")
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair.stage == "review"
    assert pair.seeded_expected == "FAIL"
    assert pair.clean_expected == "PASS"
    # the seeded diff deletes the length test that would catch the off-by-one
    assert not (pair.seeded / "head" / "test_calc.py").exists()
    assert (pair.clean / "head" / "test_calc.py").exists()


# --- grading logic -------------------------------------------------------------


def test_is_discriminating_true_only_when_seeded_fails_and_clean_passes():
    assert is_discriminating("FAIL", "PASS") is True
    assert is_discriminating("PASS", "PASS") is False  # seeded not caught
    assert is_discriminating("FAIL", "FAIL") is False  # clean twin fails too
    assert is_discriminating("PASS", "FAIL") is False


# --- evaluate + cost aggregation -----------------------------------------------


def test_evaluate_matrix_grades_discrimination(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "FAIL", "clean": "PASS"})
    rows = evaluate_matrix(
        parse_matrix("claude-code:claude-sonnet-5"), tmp_path, adapter=adapter
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.seeded_verdict == "FAIL"
    assert row.clean_verdict == "PASS"
    assert row.discriminating is True
    assert row.blocked is False
    # both twins ran through the adapter
    assert {c[3] for c in adapter.calls} == {"seeded", "clean"}


def test_evaluate_matrix_flags_nondiscriminating(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "PASS", "clean": "PASS"})
    rows = evaluate_matrix(parse_matrix("claude-code:claude-sonnet-5"), tmp_path, adapter=adapter)
    assert rows[0].discriminating is False


def test_cost_aggregation_uses_ledger_price_table(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "FAIL", "clean": "PASS"}, input_tokens=1000, output_tokens=200)
    rows = evaluate_matrix(parse_matrix("claude-code:claude-sonnet-5"), tmp_path, adapter=adapter)
    # sonnet-5 priced at (3, 15) $/Mtok; two twins: 2 * (1000/1e6*3 + 200/1e6*15)
    assert rows[0].cost_usd == pytest.approx(2 * (0.003 + 0.003))


def test_cost_is_none_for_unpriced_model(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "FAIL", "clean": "PASS"})
    rows = evaluate_matrix(parse_matrix("codex:gpt-5.5"), tmp_path, adapter=adapter)
    assert rows[0].cost_usd is None  # gpt-5.5 not in the ledger price table


def test_evaluate_matrix_blocked_cell_records_error(tmp_path):
    _make_pair(tmp_path, "review-defect")
    rows = evaluate_matrix(parse_matrix("codex:gpt-5.5"), tmp_path, adapter=ExplodingAdapter())
    assert rows[0].blocked is True
    assert rows[0].discriminating is False
    assert "auth failure" in rows[0].error


# --- run_matrix: table + summary lines -----------------------------------------


def test_run_matrix_ok_when_all_cells_discriminate(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "FAIL", "clean": "PASS"})
    ok, lines = run_matrix(
        matrix="claude-code:claude-sonnet-5", fixtures_root=tmp_path, adapter=adapter
    )
    assert ok is True
    assert lines[-1] == "eval: OK (1/1 cells discriminating)"
    body = "\n".join(lines)
    assert "claude-code:claude-sonnet-5" in body
    assert "review-defect" in body


def test_run_matrix_fail_when_a_cell_does_not_discriminate(tmp_path):
    _make_pair(tmp_path, "review-defect")
    adapter = FakeReviewAdapter({"seeded": "PASS", "clean": "PASS"})
    ok, lines = run_matrix(
        matrix="claude-code:claude-sonnet-5", fixtures_root=tmp_path, adapter=adapter
    )
    assert ok is False
    assert lines[-1] == "eval: FAIL (0/1 cells discriminating)"


def test_run_matrix_blocked_cell_fails_and_shows_error(tmp_path):
    _make_pair(tmp_path, "review-defect")
    ok, lines = run_matrix(
        matrix="codex:gpt-5.5", fixtures_root=tmp_path, adapter=ExplodingAdapter()
    )
    assert ok is False
    body = "\n".join(lines)
    assert "auth failure" in body
    assert lines[-1].startswith("eval: FAIL")


# --- dry-run -------------------------------------------------------------------


def test_dry_run_lists_cells_without_running(tmp_path):
    _make_pair(tmp_path, "review-defect")

    class Boom:
        def __call__(self, *a):
            raise AssertionError("adapter must not be called on --dry-run")

    ok, lines = run_matrix(
        matrix="claude-code:claude-sonnet-5,codex:gpt-5.5",
        fixtures_root=tmp_path, dry_run=True, adapter=Boom(),
    )
    assert ok is True
    body = "\n".join(lines)
    assert "claude-code:claude-sonnet-5" in body
    assert "codex:gpt-5.5" in body
    assert "review-defect" in body
    assert lines[-1].startswith("eval: dry-run")


# --- CLI wiring ----------------------------------------------------------------


def test_eval_parser_accepts_matrix_fixture_dry_run():
    from foundry.cli import build_parser

    args = build_parser().parse_args(
        ["eval", "--matrix", "claude-code:claude-sonnet-5", "--fixture", "review-defect", "--dry-run"]
    )
    assert args.matrix == "claude-code:claude-sonnet-5"
    assert args.fixture == "review-defect"
    assert args.dry_run is True


def test_eval_cli_dry_run_exits_zero(tmp_path, monkeypatch):
    _make_pair(tmp_path / "evals" / "fixtures" / "matrix", "review-defect")
    from foundry import cli

    monkeypatch.chdir(tmp_path)
    args = cli.build_parser().parse_args(
        ["eval", "--matrix", "claude-code:claude-sonnet-5", "--dry-run"]
    )
    assert cli._eval(args) == 0
