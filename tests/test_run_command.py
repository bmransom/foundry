"""Tests for foundry.run_command (T7): `foundry run <card-id>` end-to-end.

A scripted FakeAdapter drives a bug-fix path run on a pytest repo fixture. Asserts
the ledger event sequence (run_started … run_completed), the worktree/branch got
created, the entry path is persisted, and NO commit landed on the default branch
(AC-1.8). Unknown-card error test with near-match suggestion (AC-1.1).
"""

from datetime import datetime, timezone

import pytest

from foundry.adapters.parsers import StageResult
from foundry.board import BoardError
from foundry.run_command import run

FIXED = datetime(2026, 7, 2, 17, 0, 0, tzinfo=timezone.utc)


class FakeAdapter:
    """Records judgment/mixed calls; returns marker text the stage gates parse."""

    def __init__(self):
        self.calls = []

    def __call__(self, stage, route, workspace):
        self.calls.append(stage)
        text = ""
        if stage == "spec":
            text = "SPEC_REVIEW: CLEAN"
        elif stage == "review":
            text = "CODE_REVIEW: PASS"
        return StageResult(text=text, input_tokens=100, output_tokens=10, exit_status=0)


def test_bug_fix_run_end_to_end(tmp_path, repo_factory, git_probes):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    before = git_probes["head_sha"](repo, "main")

    adapter = FakeAdapter()
    result = run(
        "wclip-paste",
        repo_root=repo,
        path="bug-fix",
        adapter=adapter,
        now=lambda: FIXED,
    )

    assert result.outcome == "completed"

    # worktree + branch created off the default branch
    assert (repo / "wt" / "wclip-paste").is_dir()
    assert git_probes["branch_exists"](repo, "card/wclip-paste")

    # ledger rooted at the repo; event sequence run_started … run_completed
    from foundry.ledger import RunLedger

    events = RunLedger(repo).events(result.run_id)
    names = [e.event for e in events]
    assert names[0] == "run_started"
    assert names[-1] == "run_completed"
    # bug-fix skips frame/spec/plan; adapter fires for build/knowledge/review
    assert adapter.calls == ["build", "knowledge", "review"]

    # entry path persisted on run_started (resume reads this, not Driver config)
    assert events[0].stage == "bug-fix"

    # AC-1.8: no commit landed on the default branch
    assert git_probes["head_sha"](repo, "main") == before


def test_worktree_is_reused_when_present(tmp_path, repo_factory):
    repo = repo_factory(tmp_path)
    r1 = run("wclip-paste", repo_root=repo, path="bug-fix", adapter=FakeAdapter(), now=lambda: FIXED)
    # second run reuses wt/<id> and its branch rather than re-creating
    r2 = run("wclip-paste", repo_root=repo, path="bug-fix", adapter=FakeAdapter(), now=lambda: FIXED)
    assert r1.outcome == "completed" and r2.outcome == "completed"
    assert (repo / "wt" / "wclip-paste").is_dir()


def test_unknown_card_errors_with_near_match(tmp_path, repo_factory):
    repo = repo_factory(tmp_path, cards=[("wclip-paste", "Paste command")])
    with pytest.raises(BoardError) as excinfo:
        run("wclip-past", repo_root=repo, path="bug-fix", adapter=FakeAdapter())
    assert "wclip-paste" in str(excinfo.value)
