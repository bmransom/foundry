"""Tests for foundry.review.pr (T18, US-9): `foundry review <pr-number>`.

All gh and harness calls are injected — no live gh/LLM. Covers: PR resolution
parsing, isolated-worktree creation + cleanup, prompt embedding (rubric + diff),
findings parsing from a canned CODE_REVIEW output (PASS/zero findings and
FAIL/two findings — one anchored, one file-level), comment payload shape, the
gh whitelist blocking a non-whitelisted call, and `--keep` skipping cleanup.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from foundry.ledger import RunLedger
from foundry.review import pr as review_pr

FIXED = datetime(2026, 7, 2, 17, 0, 0, tzinfo=timezone.utc)

PR_VIEW_JSON = json.dumps({
    "headRefName": "fix/paste-bug",
    "headRefOid": "abc123headsha",
    "baseRefName": "main",
    "title": "Fix paste bug",
    "url": "https://github.com/acme/widget/pull/42",
})

CODE_REVIEW_PASS = "No findings.\n\nFINDINGS: []\n\nCODE_REVIEW: PASS"

CODE_REVIEW_FAIL = (
    "Two findings below.\n\n"
    "FINDINGS: "
    + json.dumps([
        {
            "severity": "blocking",
            "path": "src/widget/paste.py",
            "line": 42,
            "body": "off-by-one in the clipboard offset calc",
        },
        {
            "severity": "advisory",
            "path": "src/widget/__init__.py",
            "line": None,
            "body": "module docstring drifted from the design.md summary",
        },
    ])
    + "\n\nFLAGGED: AC-2.1\nFLAGGED: docs-sync\n\nCODE_REVIEW: FAIL"
)


# --- git repo fixture: a real local repo with a feature branch ----------------


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(root), check=True, capture_output=True, text=True,
    )


def _make_repo_with_pr_branch(root: Path) -> tuple[Path, str]:
    """A repo with main + a feature branch one commit ahead; returns (repo, head_sha)."""
    identity = ("-c", "user.email=t@t", "-c", "user.name=T")
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-b", "main")
    (root / "README.md").write_text("hello\n")
    _git(root, *identity, "add", "-A")
    _git(root, *identity, "commit", "-m", "init")
    _git(root, *identity, "checkout", "-b", "fix/paste-bug")
    (root / "feature.py").write_text("x = 1\n")
    _git(root, *identity, "add", "-A")
    _git(root, *identity, "commit", "-m", "add feature")
    head_sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    _git(root, "checkout", "main")
    return root, head_sha


class RecordingGh:
    """Injected gh call: records (argv, stdin), returns a scripted stdout per call."""

    def __init__(self, responses: dict[tuple, str] | None = None, default: str = ""):
        self.calls: list[tuple] = []
        self._responses = responses or {}
        self._default = default

    def __call__(self, argv: list[str], stdin: str | None = None) -> str:
        self.calls.append((tuple(argv), stdin))
        return self._responses.get(tuple(argv), self._default)


# --- PR resolution --------------------------------------------------------------


def test_resolve_pr_parses_gh_pr_view_json():
    gh = RecordingGh(default=PR_VIEW_JSON)
    pr = review_pr.resolve_pr(42, call=gh)

    assert pr.number == 42
    assert pr.head_ref == "fix/paste-bug"
    assert pr.head_sha == "abc123headsha"
    assert pr.base_ref == "main"
    assert pr.title == "Fix paste bug"
    assert pr.repo == "acme/widget"
    assert gh.calls[0][0] == (
        "pr", "view", "42", "--json",
        "headRefName,headRefOid,baseRefName,title,url",
    )


def test_resolve_pr_raises_on_malformed_json():
    gh = RecordingGh(default="not json")
    with pytest.raises(review_pr.ReviewError):
        review_pr.resolve_pr(42, call=gh)


# --- isolated worktree ----------------------------------------------------------


def test_create_review_worktree_is_isolated_and_checks_out_head_sha(tmp_path):
    repo, head_sha = _make_repo_with_pr_branch(tmp_path / "repo")

    worktree = review_pr.create_review_worktree(repo, head_sha)

    assert worktree.is_dir()
    assert worktree != repo
    assert not str(worktree).startswith(str(repo))  # never the current tree
    checked_out = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    assert checked_out == head_sha
    assert (worktree / "feature.py").exists()


def test_cleanup_review_worktree_removes_it(tmp_path):
    repo, head_sha = _make_repo_with_pr_branch(tmp_path / "repo")
    worktree = review_pr.create_review_worktree(repo, head_sha)
    assert worktree.exists()

    review_pr.cleanup_review_worktree(repo, worktree)

    assert not worktree.exists()
    # git no longer lists it as a live worktree
    listing = _git(repo, "worktree", "list").stdout
    assert str(worktree) not in listing


# --- diff + prompt ---------------------------------------------------------------


def test_build_diff_shows_the_feature_commit(tmp_path):
    repo, head_sha = _make_repo_with_pr_branch(tmp_path / "repo")
    worktree = review_pr.create_review_worktree(repo, head_sha)
    try:
        diff = review_pr.build_diff(repo, worktree, "main")
        assert "feature.py" in diff
        assert "+x = 1" in diff
    finally:
        review_pr.cleanup_review_worktree(repo, worktree)


def test_compile_review_prompt_embeds_rubric_and_diff():
    pr = review_pr.PullRequest(
        number=42, head_ref="fix/paste-bug", head_sha="abc123headsha",
        base_ref="main", title="Fix paste bug",
        url="https://github.com/acme/widget/pull/42", repo="acme/widget",
    )
    diff = "diff --git a/feature.py b/feature.py\n+x = 1\n"

    prompt = review_pr.compile_review_prompt(pr, diff)

    assert "Review stage rubric" in prompt  # the rubric loaded
    assert "FINDINGS:" in prompt  # the machine-parseable contract is in-prompt
    assert "#42" in prompt and "Fix paste bug" in prompt
    assert diff in prompt


# --- findings parsing (canned CODE_REVIEW output) --------------------------------


def test_parse_verdict_and_findings_pass_with_zero_findings():
    assert review_pr.parse_verdict(CODE_REVIEW_PASS) == "PASS"
    assert review_pr.parse_findings(CODE_REVIEW_PASS) == []


def test_parse_verdict_and_findings_fail_with_two_findings():
    assert review_pr.parse_verdict(CODE_REVIEW_FAIL) == "FAIL"
    findings = review_pr.parse_findings(CODE_REVIEW_FAIL)

    assert len(findings) == 2
    anchored, file_level = findings
    assert anchored.severity == "blocking"
    assert anchored.path == "src/widget/paste.py"
    assert anchored.line == 42
    assert "off-by-one" in anchored.body

    assert file_level.severity == "advisory"
    assert file_level.path == "src/widget/__init__.py"
    assert file_level.line is None
    assert "docstring" in file_level.body


def test_parse_findings_raises_when_no_findings_line():
    with pytest.raises(review_pr.FindingsParseError):
        review_pr.parse_findings("CODE_REVIEW: PASS")


def test_parse_findings_raises_on_malformed_json():
    with pytest.raises(review_pr.FindingsParseError):
        review_pr.parse_findings("FINDINGS: {not valid json\n\nCODE_REVIEW: FAIL")


# --- comment payload shape -------------------------------------------------------


def test_finding_payload_shape_anchored():
    pr = review_pr.PullRequest(
        number=42, head_ref="h", head_sha="sha1", base_ref="main", title="t",
        url="https://github.com/acme/widget/pull/42", repo="acme/widget",
    )
    finding = review_pr.Finding(
        severity="blocking", path="src/widget/paste.py", line=42, body="fix this",
    )
    payload = review_pr._finding_payload(pr, finding)
    assert payload == {
        "body": "fix this", "commit_id": "sha1", "path": "src/widget/paste.py", "line": 42,
    }


def test_finding_payload_shape_file_level_omits_line():
    pr = review_pr.PullRequest(
        number=42, head_ref="h", head_sha="sha1", base_ref="main", title="t",
        url="https://github.com/acme/widget/pull/42", repo="acme/widget",
    )
    finding = review_pr.Finding(
        severity="advisory", path="src/widget/__init__.py", line=None, body="drift",
    )
    payload = review_pr._finding_payload(pr, finding)
    assert payload == {"body": "drift", "commit_id": "sha1", "path": "src/widget/__init__.py"}
    assert "line" not in payload


def test_post_finding_calls_gh_api_pulls_comments_with_payload():
    pr = review_pr.PullRequest(
        number=42, head_ref="h", head_sha="sha1", base_ref="main", title="t",
        url="https://github.com/acme/widget/pull/42", repo="acme/widget",
    )
    finding = review_pr.Finding(
        severity="blocking", path="src/widget/paste.py", line=42, body="fix this",
    )
    gh = RecordingGh()

    review_pr.post_finding(pr, finding, call=gh)

    argv, stdin = gh.calls[0]
    assert argv[0] == "api"
    assert argv[1] == "repos/acme/widget/pulls/42/comments"
    assert "--method" in argv and "POST" in argv
    assert json.loads(stdin) == {
        "body": "fix this", "commit_id": "sha1", "path": "src/widget/paste.py", "line": 42,
    }


def test_post_summary_calls_gh_api_issues_comments_with_verdict():
    pr = review_pr.PullRequest(
        number=42, head_ref="h", head_sha="sha1", base_ref="main", title="t",
        url="https://github.com/acme/widget/pull/42", repo="acme/widget",
    )
    gh = RecordingGh()

    review_pr.post_summary(pr, "FAIL", [], call=gh)

    argv, stdin = gh.calls[0]
    assert argv[0] == "api"
    assert argv[1] == "repos/acme/widget/issues/42/comments"
    assert "--method" in argv and "POST" in argv
    assert "FAIL" in json.loads(stdin)["body"]


# --- gh whitelist (AC-9.2) -------------------------------------------------------


def test_whitelist_allows_pr_view():
    gh = RecordingGh(default="{}")
    review_pr.run_gh(["pr", "view", "1", "--json", "title"], call=gh)
    assert gh.calls  # did not raise


def test_whitelist_allows_comments_post():
    gh = RecordingGh()
    review_pr.run_gh(
        ["api", "repos/acme/widget/pulls/1/comments", "--method", "POST", "--input", "-"],
        stdin="{}", call=gh,
    )
    assert gh.calls


@pytest.mark.parametrize("argv", [
    ["pr", "review", "--approve"],
    ["pr", "review", "1", "--approve"],
    ["pr", "merge", "1"],
    ["pr", "close", "1"],
    ["api", "repos/acme/widget/pulls/1/reviews", "--method", "POST"],
    ["api", "repos/acme/widget/pulls/1/merge", "--method", "PUT"],
    ["api", "repos/acme/widget/pulls/1/comments"],  # comments endpoint but no POST
    ["api", "repos/acme/widget/pulls/1/comments", "--method", "DELETE", "--field", "POST"],
    # DELETE with a stray "POST" token elsewhere in argv — membership alone would
    # wrongly allow this; only an adjacent `--method POST` pair may pass.
])
def test_whitelist_blocks_non_whitelisted_calls(argv):
    gh = RecordingGh()
    with pytest.raises(review_pr.GhWhitelistError):
        review_pr.run_gh(argv, call=gh)
    assert gh.calls == []  # never reached the injected call


# --- end-to-end run_review: fake gh + fake harness -------------------------------


class FakeHarnessRun:
    """Injected adapters.headless `run`: returns a scripted stream-json transcript."""

    def __init__(self, text: str):
        self._text = text
        self.calls = []

    def __call__(self, argv, workspace, stdin=None):
        self.calls.append((argv, workspace, stdin))
        event = {
            "type": "result", "is_error": False, "result": self._text,
            "usage": {"input_tokens": 500, "output_tokens": 50},
        }
        return json.dumps(event) + "\n"


def test_run_review_end_to_end_posts_findings_and_cleans_up(tmp_path):
    repo, head_sha = _make_repo_with_pr_branch(tmp_path / "repo")
    view_json = json.dumps({
        "headRefName": "fix/paste-bug", "headRefOid": head_sha, "baseRefName": "main",
        "title": "Fix paste bug", "url": "https://github.com/acme/widget/pull/42",
    })
    gh = RecordingGh(default=view_json)
    harness_run = FakeHarnessRun(CODE_REVIEW_FAIL)

    result = review_pr.run_review(
        42, repo_root=repo, gh_call=gh, harness_run=harness_run, now=lambda: FIXED,
    )

    assert result.verdict == "FAIL"
    assert len(result.findings) == 2
    assert result.worktree is None  # cleaned up (no --keep)

    # two finding comments + one summary comment, each a POST to a comments endpoint
    api_calls = [c for c in gh.calls if c[0][0] == "api"]
    assert len(api_calls) == 3
    assert api_calls[0][0][1] == "repos/acme/widget/pulls/42/comments"
    assert api_calls[1][0][1] == "repos/acme/widget/pulls/42/comments"
    assert api_calls[2][0][1] == "repos/acme/widget/issues/42/comments"

    # no gh subcommand other than pr view / api ...comments POST was ever invoked
    for argv, _ in gh.calls:
        assert argv[0] in ("pr", "api")
        if argv[0] == "pr":
            assert argv[1] in ("view", "diff")

    # the worktree used by the harness is gone
    used_workspace = Path(harness_run.calls[0][1])
    assert not used_workspace.exists()

    # ledger recorded the run under review/harness/model/tokens/cost
    events = RunLedger(repo).events(result.run_id)
    assert events[0].event == "run_started"
    assert events[-1].event == "run_completed"
    completed = next(e for e in events if e.event == "stage_completed")
    assert completed.stage == "review"
    assert completed.input_tokens == 500
    assert completed.output_tokens == 50
    assert completed.model is not None


def test_run_review_keep_skips_cleanup(tmp_path):
    repo, head_sha = _make_repo_with_pr_branch(tmp_path / "repo")
    view_json = json.dumps({
        "headRefName": "fix/paste-bug", "headRefOid": head_sha, "baseRefName": "main",
        "title": "Fix paste bug", "url": "https://github.com/acme/widget/pull/42",
    })
    gh = RecordingGh(default=view_json)
    harness_run = FakeHarnessRun(CODE_REVIEW_PASS)

    result = review_pr.run_review(
        42, repo_root=repo, keep=True, gh_call=gh, harness_run=harness_run, now=lambda: FIXED,
    )

    assert result.verdict == "PASS"
    assert result.findings == []
    assert result.worktree is not None
    assert result.worktree.exists()

    # cleanup, since the test fixture must not leak a real worktree
    review_pr.cleanup_review_worktree(repo, result.worktree)


# --- CLI wiring -------------------------------------------------------------------


def test_review_parser_accepts_pr_number_and_keep_flag():
    from foundry.cli import build_parser

    args = build_parser().parse_args(["review", "42", "--keep"])
    assert args.pr_number == 42
    assert args.keep is True


def test_review_parser_keep_defaults_false():
    from foundry.cli import build_parser

    args = build_parser().parse_args(["review", "42"])
    assert args.keep is False


def test_review_cli_dispatches_to_run_review(monkeypatch, tmp_path):
    from foundry import cli
    from foundry.review import pr as review_pr_module

    captured = {}

    def fake_run_review(pr_number, *, repo_root, keep):
        captured.update(pr_number=pr_number, repo_root=repo_root, keep=keep)
        return review_pr_module.ReviewResult(
            run_id="r-1", verdict="PASS", findings=[],
            pr=review_pr_module.PullRequest(
                number=pr_number, head_ref="h", head_sha="s", base_ref="main",
                title="t", url="https://github.com/acme/widget/pull/42", repo="acme/widget",
            ),
            worktree=None,
        )

    monkeypatch.setattr(review_pr_module, "run_review", fake_run_review)
    monkeypatch.chdir(tmp_path)
    args = cli.build_parser().parse_args(["review", "42", "--keep"])
    rc = cli._review(args)

    assert rc == 0
    assert captured == {"pr_number": 42, "repo_root": tmp_path, "keep": True}


def test_run_review_never_approves_merges_or_dismisses():
    """AC-9.2, exercised at the whitelist boundary directly (the strongest
    guarantee independent of what a scripted harness or gh stub might return)."""
    forbidden = [
        ["pr", "review", "1", "--approve"],
        ["pr", "merge", "1", "--auto"],
        ["pr", "close", "1"],
    ]
    for argv in forbidden:
        with pytest.raises(review_pr.GhWhitelistError):
            review_pr.run_gh(argv, call=RecordingGh())
