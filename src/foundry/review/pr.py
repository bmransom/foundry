"""The PR-review runner (T18, US-9): `foundry review <pr-number>` runs the review
stage headlessly against a GitHub PR and posts findings as anchored PR comments.
Transport only — the richer comment-thread conversation (replies, resolution
tracking) is the separate pr-deliberation card; this module posts once per finding
plus one summary comment, and never approves, merges, or dismisses (AC-9.2).

Every `gh` call funnels through `run_gh`, which is whitelist-enforcing: only
`pr view` (resolve), `pr diff` (reserved, unused today — this module builds the
diff with plain `git diff` inside the isolated worktree instead), and
`api .../comments --method POST` (the write path) may pass. Any other gh
subcommand — `pr review --approve`, `pr merge`, `pr close`, a non-comments `api`
call — raises `GhWhitelistError` before a subprocess ever spawns.

Seam: `compile_review_prompt` is a review-specific compile, not
`driver.prompts.compile_stage_prompt` — that function's `CardContext` has no slot
for an arbitrary diff blob or PR metadata, and threading one through would leak PR
vocabulary into the driver's stage-prompt contract (design D8 keeps that
mechanical, card-shaped). This module loads the same `rubrics/review.md` via
`driver.prompts.load_rubric` and assembles PR context + diff itself.

Findings transport: `rubrics/review.md`'s prior output contract had prose findings
plus a `FLAGGED: <signature>` footer with no file:line or comment body — not
machine-parseable into a PR comment payload. T18 extends the rubric with a
`FINDINGS:` line (a single-line JSON array); this module's `parse_findings` reads
it the same way the driver's marker gates read `SPEC_REVIEW:`/`CODE_REVIEW:`.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from foundry import adapters
from foundry.config import Config
from foundry.driver.prompts import load_rubric
from foundry.ledger import RunEvent, RunLedger, compute_cost, new_run_id

GhCall = Callable[..., str]  # (argv: list[str], stdin: str | None) -> stdout text

_SEPARATOR = "\n\n---\n\n"
_FINDINGS_PREFIX = "FINDINGS:"
_VERDICT_PREFIX = "CODE_REVIEW:"
_COMMENTS_ENDPOINT = re.compile(r"^repos/[^/]+/[^/]+/(pulls|issues)/\d+/comments$")
_PR_URL_RE = re.compile(r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?/pull/\d+")


class ReviewError(Exception):
    """PR resolution, diff, or findings parsing failed."""


class FindingsParseError(ReviewError):
    """The review stage's output had no `FINDINGS:` line, or it was not valid JSON."""


class GhWhitelistError(ReviewError):
    """A gh call outside {pr view, pr diff, api .../comments POST} was attempted
    (AC-9.2: `foundry review` never approves, merges, or dismisses)."""


# --- the one gh seam (AC-9.2) ---------------------------------------------------


def _enforce_whitelist(argv: list) -> None:
    if len(argv) >= 2 and argv[0] == "pr" and argv[1] in ("view", "diff"):
        return
    if (
        argv
        and argv[0] == "api"
        and len(argv) >= 2
        and _COMMENTS_ENDPOINT.match(argv[1])
        and "POST" in argv
    ):
        return
    raise GhWhitelistError(
        f"gh call not whitelisted: {argv!r} — only 'pr view', 'pr diff', and "
        f"'api .../comments --method POST' are permitted; foundry review never "
        f"approves, merges, or dismisses (AC-9.2)"
    )


def _default_gh_call(argv: list, stdin: str | None = None) -> str:
    proc = subprocess.run(
        ["gh", *argv], input=stdin, capture_output=True, text=True, check=True,
    )
    return proc.stdout


def run_gh(argv: list, *, stdin: str | None = None, call: Optional[GhCall] = None) -> str:
    """Whitelist-check `argv`, then delegate to `call` (injectable for tests;
    defaults to a real `gh` subprocess — argv list, no shell)."""
    _enforce_whitelist(argv)
    call = call or _default_gh_call
    return call(argv, stdin)


# --- PR resolution (AC-9.1a) -----------------------------------------------------


@dataclass(frozen=True)
class PullRequest:
    number: int
    head_ref: str
    head_sha: str
    base_ref: str
    title: str
    url: str
    repo: str  # "owner/name", parsed from url


def _repo_from_url(url: str) -> str:
    match = _PR_URL_RE.search(url)
    if not match:
        raise ReviewError(f"could not parse owner/repo from PR url: {url!r}")
    return match.group("repo")


def resolve_pr(number: int, *, call: Optional[GhCall] = None) -> PullRequest:
    """Resolve a PR's head/base/title/url via `gh pr view --json ...` (AC-9.1)."""
    out = run_gh(
        ["pr", "view", str(number), "--json",
         "headRefName,headRefOid,baseRefName,title,url"],
        call=call,
    )
    try:
        data = json.loads(out)
    except json.JSONDecodeError as e:
        raise ReviewError(f"gh pr view returned non-JSON output: {e}") from e
    return PullRequest(
        number=number,
        head_ref=data["headRefName"],
        head_sha=data["headRefOid"],
        base_ref=data["baseRefName"],
        title=data["title"],
        url=data["url"],
        repo=_repo_from_url(data["url"]),
    )


# --- isolated worktree (AC-9.1b) -------------------------------------------------


def create_review_worktree(repo_root: Path, head_sha: str) -> Path:
    """`git worktree add <tmp path> <head_sha>` — never the current tree."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="foundry-review-"))
    worktree = tmp_dir / "pr"
    subprocess.run(
        ["git", "worktree", "add", str(worktree), head_sha],
        cwd=str(repo_root), check=True, capture_output=True, text=True,
    )
    return worktree


def cleanup_review_worktree(repo_root: Path, worktree: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", str(worktree), "--force"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    import shutil
    shutil.rmtree(worktree.parent, ignore_errors=True)


def _ref_exists(repo_root: Path, ref: str) -> bool:
    return subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=str(repo_root), capture_output=True,
    ).returncode == 0


def build_diff(repo_root: Path, worktree: Path, base_ref: str) -> str:
    """`git diff base...head` inside the worktree (AC-9.1c); prefers
    `origin/<base>` when the repo has it (the common cloned-checkout case)."""
    base = f"origin/{base_ref}" if _ref_exists(repo_root, f"origin/{base_ref}") else base_ref
    proc = subprocess.run(
        ["git", "diff", f"{base}...HEAD"],
        cwd=str(worktree), capture_output=True, text=True, check=True,
    )
    return proc.stdout


# --- prompt (AC-9.1c) -------------------------------------------------------------


def compile_review_prompt(pr: PullRequest, diff: str) -> str:
    """Review-specific compile — see module docstring's seam note. The review
    rubric, PR context, and the PR diff, deterministic given those inputs."""
    rubric = load_rubric("review")
    context = (
        "## PR context\n\n"
        f"- PR: #{pr.number} — {pr.title}\n"
        f"- URL: {pr.url}\n"
        f"- Base: {pr.base_ref}\n"
        f"- Head: {pr.head_ref} ({pr.head_sha})"
    )
    diff_block = f"## Diff (base...head)\n\n```diff\n{diff}```"
    return _SEPARATOR.join([rubric, context, diff_block]) + "\n"


# --- findings parsing (AC-9.1d/e) -------------------------------------------------


@dataclass(frozen=True)
class Finding:
    severity: str
    path: str
    line: Optional[int]
    body: str


def _last_marker_value(text: str, prefix: str) -> Optional[str]:
    value = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(prefix):
            value = line[len(prefix):].strip()
    return value


def parse_verdict(text: str) -> str:
    return _last_marker_value(text, _VERDICT_PREFIX) or "FAIL"


def parse_findings(text: str) -> list:
    """Parse the rubric's `FINDINGS:` line (the machine-parseable findings block
    T18 added to rubrics/review.md — the prose findings body has no stable shape
    to post as anchored comments)."""
    raw = _last_marker_value(text, _FINDINGS_PREFIX)
    if raw is None:
        raise FindingsParseError("no 'FINDINGS:' line in review output")
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise FindingsParseError(f"FINDINGS: line is not valid JSON: {e}") from e
    return [
        Finding(
            severity=item["severity"], path=item["path"],
            line=item.get("line"), body=item["body"],
        )
        for item in items
    ]


# --- posting (AC-9.1f, AC-9.2) ---------------------------------------------------


def _finding_payload(pr: PullRequest, finding: Finding) -> dict:
    payload = {"body": finding.body, "commit_id": pr.head_sha, "path": finding.path}
    if finding.line is not None:
        payload["line"] = finding.line
    return payload


def post_finding(pr: PullRequest, finding: Finding, *, call: Optional[GhCall] = None) -> None:
    """One injectable gh call per finding — never batched."""
    payload = _finding_payload(pr, finding)
    run_gh(
        ["api", f"repos/{pr.repo}/pulls/{pr.number}/comments",
         "--method", "POST", "--input", "-"],
        stdin=json.dumps(payload), call=call,
    )


def post_summary(pr: PullRequest, verdict: str, findings: list, *, call: Optional[GhCall] = None) -> None:
    """One summary comment with the verdict (AC-9.1f) — a regular PR conversation
    comment (the `issues/.../comments` endpoint; a PR is an issue in GitHub's API),
    since a summary has no single file:line to anchor to."""
    body = f"CODE_REVIEW: {verdict}\n\n{len(findings)} finding(s) posted by `foundry review`."
    run_gh(
        ["api", f"repos/{pr.repo}/issues/{pr.number}/comments",
         "--method", "POST", "--input", "-"],
        stdin=json.dumps({"body": body}), call=call,
    )


# --- ledger + orchestration -------------------------------------------------------


@dataclass(frozen=True)
class ReviewResult:
    run_id: str
    verdict: str
    findings: list
    pr: PullRequest
    worktree: Optional[Path]  # only set (and left behind) when keep=True


def run_review(
    pr_number: int,
    *,
    repo_root: Path | str,
    keep: bool = False,
    gh_call: Optional[GhCall] = None,
    harness_run: Optional[Callable] = None,
    ledger: Optional[RunLedger] = None,
    now: Optional[Callable[[], datetime]] = None,
) -> ReviewResult:
    """Resolve the PR, check out its head into an isolated worktree, run the
    review stage headlessly through the routed harness, post findings + a
    summary comment, and clean up the worktree unless `keep` (AC-9.1).

    `gh_call` and `harness_run` are the injectable seams (a scripted fake gh and
    a scripted fake `adapters.headless` runner in tests); `ledger` defaults to
    the repo's `.foundry/runs/` ledger, appended to like any driver run.
    """
    repo_root = Path(repo_root)
    config = Config.load(repo_root)
    ledger = ledger or RunLedger(repo_root)
    run_id = new_run_id(now() if now else None)
    card_id = f"pr-{pr_number}"

    def ts() -> str:
        moment = now() if now else datetime.now(timezone.utc)
        return moment.strftime("%Y-%m-%dT%H:%M:%SZ")

    ledger.append(RunEvent(
        run_id=run_id, card_id=card_id, stage="review", event="run_started", ts=ts(),
    ))

    pr = resolve_pr(pr_number, call=gh_call)
    worktree = create_review_worktree(repo_root, pr.head_sha)
    try:
        diff = build_diff(repo_root, worktree, pr.base_ref)
        prompt = compile_review_prompt(pr, diff)

        route = config.route_for("review")
        harness = adapters.load(route.harness)
        tmp_dir = worktree / ".foundry" / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        prompt_file = tmp_dir / "review-prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")

        ledger.append(RunEvent(
            run_id=run_id, card_id=card_id, stage="review", event="stage_started", ts=ts(),
            harness=route.harness, model=route.model, effort=route.effort,
        ))
        result = adapters.headless(harness, str(prompt_file), route, str(worktree), run=harness_run)

        verdict = parse_verdict(result.text)
        findings = parse_findings(result.text)
        cost = compute_cost(route.model, result.input_tokens, result.output_tokens)

        ledger.append(RunEvent(
            run_id=run_id, card_id=card_id, stage="review", event="gate_evaluated", ts=ts(),
            harness=route.harness, model=route.model, effort=route.effort,
            gate={"name": "CODE_REVIEW", "outcome": verdict},
        ))
        ledger.append(RunEvent(
            run_id=run_id, card_id=card_id, stage="review", event="stage_completed", ts=ts(),
            harness=route.harness, model=route.model, effort=route.effort,
            input_tokens=result.input_tokens, output_tokens=result.output_tokens,
            cost_usd=cost, gate={"name": "CODE_REVIEW", "outcome": verdict},
        ))

        for finding in findings:
            post_finding(pr, finding, call=gh_call)
        post_summary(pr, verdict, findings, call=gh_call)

        ledger.append(RunEvent(
            run_id=run_id, card_id=card_id, stage=None, event="run_completed", ts=ts(),
        ))
    finally:
        if not keep:
            cleanup_review_worktree(repo_root, worktree)

    return ReviewResult(
        run_id=run_id, verdict=verdict, findings=findings, pr=pr,
        worktree=worktree if keep else None,
    )
