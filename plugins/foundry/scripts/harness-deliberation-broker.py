#!/usr/bin/env python3
"""Storage primitives for Foundry harness deliberation sessions."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable


REQUIRED_HARNESSES = ["codex", "claude-code"]
REQUIRED_COMMANDS = ["tmux", "git", "codex", "claude"]
TURN_SLUG_BY_HARNESS = {
    "codex": "codex",
    "claude-code": "claude",
}
REQUIRED_GUIDANCE_PATHS = [
    "AGENTS.md",
    "knowledge/glossary.md",
    "roadmap/specs/README.md",
    "roadmap/ROADMAP.md",
]
DEFAULT_LIVE_SMOKE_PROMPT = """Opt-in harness deliberation live smoke.

Return one concise sentence confirming that you received the harness deliberation prompt.
Do not edit files, run tools, or propose repository changes.
"""
DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD = "0.25"

KNOWN_EVENT_TYPES = {
    "session_started",
    "mediator_prompt",
    "repo_guidance",
    "participant_final",
    "participant_failed",
    "participant_limited",
    "question",
    "decision",
    "snapshot",
    "truncation",
    "stall",
}

VALID_DECISION_DISPOSITIONS = {"settled", "rejected", "deferred-dissent"}
PROGRESS_EVENT_TYPES = {"question", "decision", "snapshot", "truncation"}

RESERVED_EVENT_FIELDS = {"event_id", "type", "created_at", "session_id"}


class CommandResult:
    def __init__(self, exit_code: int, stdout: str, stderr: str) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class PreflightResult:
    def __init__(self, failures: list[dict[str, str]]) -> None:
        self.failures = failures

    @property
    def ok(self) -> bool:
        return not self.failures


class StartResult:
    def __init__(
        self,
        *,
        session_dir: Path,
        tmux_session: str,
        tmux_commands: list[list[str]],
        attach_command: str,
    ) -> None:
        self.session_dir = session_dir
        self.tmux_session = tmux_session
        self.tmux_commands = tmux_commands
        self.attach_command = attach_command


class ParticipantResult:
    def __init__(self, *, final: str, raw: str = "") -> None:
        self.final = final
        self.raw = raw


class ParticipantLimited(Exception):
    def __init__(
        self,
        *,
        actor: str,
        category: str,
        detail: str,
        retry_at: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.actor = actor
        self.category = category
        self.detail = detail
        self.retry_at = retry_at


class ParticipantFailed(Exception):
    def __init__(self, *, actor: str, exit_code: int, detail: str) -> None:
        super().__init__(detail)
        self.actor = actor
        self.exit_code = exit_code
        self.detail = detail


def run_start_preflight(
    *,
    repo_root: Path | str,
    command_exists: Callable[[str], bool] | None = None,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
    harness_status_checker: Callable[[Path, list[str]], list[dict[str, object]]]
    | None = None,
) -> PreflightResult:
    repo = Path(repo_root)
    command_exists = command_exists or _command_exists
    command_runner = command_runner or _run_command
    harness_status_checker = harness_status_checker or _check_harness_statuses
    failures: list[dict[str, str]] = []

    for command in REQUIRED_COMMANDS:
        if not command_exists(command):
            failures.append(
                {
                    "check": "command",
                    "command": command,
                    "message": f"missing required command: {command}",
                }
            )

    if command_exists("git"):
        result = command_runner(["git", "worktree", "list"], 10)
        if result.exit_code != 0:
            failures.append(
                {
                    "check": "git-worktree",
                    "command": "git worktree",
                    "message": "git worktree failed",
                }
            )

    manifest = _read_manifest(repo, failures)
    present_harnesses: list[str] = []
    if manifest:
        value = manifest.get("harnesses", [])
        if isinstance(value, list):
            present_harnesses = [str(item) for item in value]
            missing = [
                harness
                for harness in REQUIRED_HARNESSES
                if harness not in present_harnesses
            ]
            if missing:
                failures.append(
                    {
                        "check": "manifest-harnesses",
                        "command": ".foundry/manifest.json",
                        "message": (
                            "missing harnesses: "
                            f"{', '.join(missing)}; present: {_comma_list(present_harnesses)}"
                        ),
                    }
                )
        else:
            failures.append(
                {
                    "check": "manifest-harnesses",
                    "command": ".foundry/manifest.json",
                    "message": ".foundry/manifest.json harnesses must be a list",
                }
            )

    for relative_path in REQUIRED_GUIDANCE_PATHS:
        if not (repo / relative_path).is_file():
            failures.append(
                {
                    "check": "repo-guidance",
                    "command": relative_path,
                    "message": f"missing required repo guidance: {relative_path}",
                }
            )

    if manifest and not [
        failure for failure in failures if failure["check"] == "command"
    ]:
        for status in harness_status_checker(repo, REQUIRED_HARNESSES):
            if status.get("category") != "ok":
                failures.append(
                    {
                        "check": "harness-status",
                        "command": str(
                            status.get("command", status.get("harness", ""))
                        ),
                        "message": (
                            f"{status.get('harness')}: {status.get('category')}"
                            + (
                                f" - {status.get('detail')}"
                                if status.get("detail")
                                else ""
                            )
                        ),
                    }
                )

    return PreflightResult(failures)


def start_session(
    *,
    repo_root: Path | str,
    prompt_file: Path | str,
    session_id: str,
    attach: bool = False,
    is_interactive: bool = False,
    base_commit: str | None = None,
    command_exists: Callable[[str], bool] | None = None,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
    harness_status_checker: Callable[[Path, list[str]], list[dict[str, object]]]
    | None = None,
    run_tmux: bool = True,
) -> StartResult:
    repo = Path(repo_root)
    prompt_path = Path(prompt_file)
    preflight = run_start_preflight(
        repo_root=repo,
        command_exists=command_exists,
        command_runner=command_runner,
        harness_status_checker=harness_status_checker,
    )
    if not preflight.ok:
        messages = "\n".join(failure["message"] for failure in preflight.failures)
        raise ValueError(f"preflight failed:\n{messages}")

    session_dir = repo / ".foundry/tmp/harness-deliberation" / session_id
    base = base_commit or _git_head(repo, command_runner or _run_command)
    store = SessionStore.create(
        session_dir=session_dir,
        session_id=session_id,
        repo_root=repo,
        base_commit=base,
        participants=REQUIRED_HARNESSES,
        config={"stall_rounds": 2},
    )
    prompt_payload = store.write_payload("mediator/prompt.md", prompt_path.read_bytes())
    store.append_event(
        "session_started",
        {
            "actor": "broker",
            "repo_root": str(repo),
            "base_commit": base,
            "participants": REQUIRED_HARNESSES,
            "config": {"stall_rounds": 2},
        },
    )
    store.append_event(
        "mediator_prompt",
        {
            "actor": "mediator",
            "payloads": {"prompt": prompt_payload},
        },
    )

    tmux_session = f"foundry-hd-{session_id}"
    tmux_commands = build_tmux_commands(
        repo_root=repo,
        session_dir=session_dir,
        tmux_session=tmux_session,
    )
    if run_tmux:
        runner = command_runner or _run_command
        for command in tmux_commands:
            result = runner(command, 10)
            if result.exit_code != 0:
                raise RuntimeError(f"tmux command failed: {' '.join(command)}")
        if attach and is_interactive:
            result = runner(["tmux", "attach", "-t", tmux_session], 10)
            if result.exit_code != 0:
                raise RuntimeError(f"tmux attach failed: {tmux_session}")

    return StartResult(
        session_dir=session_dir,
        tmux_session=tmux_session,
        tmux_commands=tmux_commands,
        attach_command=f"tmux attach -t {tmux_session}",
    )


def build_tmux_commands(
    *,
    repo_root: Path,
    session_dir: Path,
    tmux_session: str,
) -> list[list[str]]:
    return [
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            tmux_session,
            "-n",
            "control",
            "-c",
            str(repo_root),
            "printf 'codex pane\\n'",
        ],
        [
            "tmux",
            "split-window",
            "-t",
            f"{tmux_session}:control",
            "-h",
            "printf 'claude-code pane\\n'",
        ],
        [
            "tmux",
            "split-window",
            "-t",
            f"{tmux_session}:control",
            "-v",
            "printf 'mediator command shell\\n'",
        ],
        [
            "tmux",
            "new-window",
            "-t",
            tmux_session,
            "-n",
            "state",
            "-c",
            str(repo_root),
            f"tail -f {session_dir / 'transcript.md'} {session_dir / 'state.md'}",
        ],
    ]


def run_round(
    *,
    session_dir: Path | str,
    participant_runner: Callable[[str, Path, Path], ParticipantResult],
) -> None:
    store = SessionStore.open(session_dir)
    repo = Path(store.session["repo_root"])
    events = store._events()
    round_id, remaining, is_new_round = _resume_round(events)
    mediator_prompt = (store.session_dir / "mediator/prompt.md").read_text(
        encoding="utf-8"
    )

    if is_new_round:
        guidance = build_repo_guidance(repo)
        store.append_event(
            "repo_guidance",
            {
                "actor": "broker",
                "round_id": round_id,
                "guidance": guidance,
            },
        )
    else:
        guidance = _guidance_for_round(events, round_id)

    peer_finals: list[dict[str, str]] = _peer_finals_for_round(store, round_id)
    for actor in remaining:
        turn_id = _next_turn_id(store._events(), actor)
        turn_dir = store.session_dir / "turns" / turn_id
        prompt_text = _render_participant_prompt(
            session_id=store.session_id,
            actor=actor,
            round_id=round_id,
            mediator_prompt=mediator_prompt,
            guidance=guidance,
            state_md=_current_state_md(store),
            peer_finals=peer_finals,
        )
        prompt_payload = store.write_payload(f"turns/{turn_id}/prompt.md", prompt_text)
        prompt_path = turn_dir / "prompt.md"
        raw_path = turn_dir / "raw.log"

        try:
            result = participant_runner(actor, prompt_path, raw_path)
        except ParticipantLimited as exc:
            event: dict[str, Any] = {
                "actor": exc.actor,
                "round_id": round_id,
                "turn_id": turn_id,
                "category": exc.category,
                "detail": exc.detail,
                "payloads": {"prompt": prompt_payload},
            }
            if exc.retry_at:
                event["retry_at"] = exc.retry_at
            store.append_event("participant_limited", event)
            store.render_views()
            return
        except ParticipantFailed as exc:
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_text(f"{exc.detail}\n", encoding="utf-8")
            store.append_event(
                "participant_failed",
                {
                    "actor": exc.actor,
                    "round_id": round_id,
                    "turn_id": turn_id,
                    "exit_code": exc.exit_code,
                    "detail": exc.detail,
                    "payloads": {"prompt": prompt_payload},
                    "raw_path": f"turns/{turn_id}/raw.log",
                },
            )
            store.render_views()
            return

        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(result.raw, encoding="utf-8")
        final_payload = store.write_payload(f"turns/{turn_id}/final.md", result.final)
        store.append_event(
            "participant_final",
            {
                "actor": actor,
                "round_id": round_id,
                "turn_id": turn_id,
                "payloads": {"prompt": prompt_payload, "final": final_payload},
                "raw_path": f"turns/{turn_id}/raw.log",
            },
        )
        peer_finals.append(
            {
                "actor": actor,
                "path": final_payload["path"],
                "content": result.final,
            }
        )

    _maybe_emit_stall(store, round_id)
    store.render_views()


def run_live_smoke(
    *,
    repo_root: Path | str,
    session_id: str,
    prompt_file: Path | str | None = None,
    prompt_text: str | None = None,
    participant_runner: Callable[[str, Path, Path], ParticipantResult] | None = None,
    command_exists: Callable[[str], bool] | None = None,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
    harness_status_checker: Callable[[Path, list[str]], list[dict[str, object]]]
    | None = None,
    timeout_s: int = 180,
    claude_budget_usd: str = DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD,
    run_tmux: bool = False,
) -> dict[str, object]:
    repo = Path(repo_root).resolve()
    runner = command_runner or _run_command
    before_status = _git_status_snapshot(repo, runner)
    prompt_path = _materialize_live_smoke_prompt(
        repo=repo,
        session_id=session_id,
        prompt_file=prompt_file,
        prompt_text=prompt_text,
    )
    started = start_session(
        repo_root=repo,
        prompt_file=prompt_path,
        session_id=session_id,
        attach=False,
        is_interactive=False,
        command_exists=command_exists,
        command_runner=runner,
        harness_status_checker=harness_status_checker,
        run_tmux=run_tmux,
    )
    live_runner = participant_runner or _live_participant_runner(
        repo,
        timeout_s,
        claude_budget_usd,
    )
    run_round(session_dir=started.session_dir, participant_runner=live_runner)
    after_status = _git_status_snapshot(repo, runner)
    if after_status != before_status:
        raise RuntimeError(
            "consumer repo worktree changed during live smoke:\n"
            + _status_diff(before_status, after_status)
        )

    final_events = [
        event
        for event in SessionStore.open(started.session_dir)._events()
        if event.get("type") == "participant_final"
    ]
    if len(final_events) != len(REQUIRED_HARNESSES):
        raise RuntimeError("live smoke did not record final.md for both participants")
    for event in final_events:
        final_path = started.session_dir / event["payloads"]["final"]["path"]
        _assert_final_shape(event["actor"], final_path.read_text(encoding="utf-8"))
    return {
        "session_dir": str(started.session_dir),
        "participants": [event["actor"] for event in final_events],
        "finals": [
            {
                "actor": event["actor"],
                "path": event["payloads"]["final"]["path"],
            }
            for event in final_events
        ],
        "worktree_unchanged": True,
    }


FINAL_MIN_CHARS = 16


def _assert_final_shape(actor: str, final: str) -> None:
    """Reject an empty or boilerplate final so a no-op cannot pass as success."""
    if len(final.strip()) < FINAL_MIN_CHARS:
        raise RuntimeError(
            f"{actor} final is empty or too short to be a real turn "
            f"({len(final.strip())} chars < {FINAL_MIN_CHARS})"
        )


def apply_decisions(
    *,
    session_dir: Path | str,
    questions: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
) -> None:
    store = SessionStore.open(session_dir)
    known_questions = _known_question_ids(store._events())
    for question in questions or []:
        question_id = _required_string(question, "question_id")
        text = _required_string(question, "text")
        event: dict[str, Any] = {
            "actor": question.get("actor", "mediator"),
            "question_id": question_id,
            "text": text,
        }
        if question.get("supersedes"):
            event["supersedes"] = question["supersedes"]
        store.append_event("question", event)
        known_questions.add(question_id)

    decision_events = _decision_event_ids(store._events())
    for decision in decisions or []:
        decision_id = _required_string(decision, "decision_id")
        question_id = _required_string(decision, "question_id")
        disposition = _required_string(decision, "disposition")
        if disposition not in VALID_DECISION_DISPOSITIONS:
            raise ValueError(f"invalid disposition for {decision_id}: {disposition}")
        if question_id not in known_questions:
            raise ValueError(f"unknown question_id for {decision_id}: {question_id}")
        supersedes = decision.get("supersedes")
        if supersedes and supersedes not in decision_events:
            raise ValueError(f"supersedes must name a decision event_id: {supersedes}")
        event = {
            "actor": decision.get("actor", "mediator"),
            "decision_id": decision_id,
            "question_id": question_id,
            "disposition": disposition,
            "summary": _required_string(decision, "summary"),
        }
        if supersedes:
            event["supersedes"] = supersedes
        if "outputs" in decision:
            event["outputs"] = decision["outputs"]
        if "payloads" in decision:
            event["payloads"] = decision["payloads"]
        appended = store.append_event("decision", event)
        decision_events.add(appended["event_id"])

    store.render_views()


def apply_decision_file(*, session_dir: Path | str, decision_file: Path | str) -> None:
    payload = _read_json(Path(decision_file))
    apply_decisions(
        session_dir=session_dir,
        questions=payload.get("questions", []),
        decisions=payload.get("decisions", []),
    )


def create_scratch_worktrees(
    *,
    session_dir: Path | str,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
) -> list[dict[str, str]]:
    store = SessionStore.open(session_dir)
    repo = Path(store.session["repo_root"])
    base_commit = store.session["base_commit"]
    runner = command_runner or _run_command
    scratch_root = store.session_dir / "scratch"

    result: list[dict[str, str]] = []
    for actor in REQUIRED_HARNESSES:
        slug = TURN_SLUG_BY_HARNESS.get(actor, actor.replace("-code", ""))
        path = scratch_root / slug
        if path.exists():
            raise ValueError(f"scratch worktree exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        branch = f"foundry/hd/{_branch_slug(store.session_id)}/{slug}"
        command = [
            "git",
            "-C",
            str(repo),
            "worktree",
            "add",
            "-b",
            branch,
            str(path),
            base_commit,
        ]
        completed = runner(command, 60)
        if completed.exit_code != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"scratch worktree failed for {actor}: {detail}")
        result.append(
            {
                "actor": actor,
                "branch": branch,
                "path": str(path),
                "base_commit": base_commit,
            }
        )

    return result


def capture_snapshot(
    *,
    session_dir: Path | str,
    actor: str,
    byte_ceiling: int | None = None,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
) -> dict[str, Any]:
    store = SessionStore.open(session_dir)
    runner = command_runner or _run_command
    slug = TURN_SLUG_BY_HARNESS.get(actor, actor.replace("-code", ""))
    worktree = store.session_dir / "scratch" / slug
    if not worktree.is_dir():
        raise ValueError(f"scratch worktree missing: {actor}")

    snapshot_id = f"{_next_snapshot_number(store._events()):04d}-{slug}"
    snapshot_root = f"snapshots/{snapshot_id}"
    branch_result = runner(["git", "-C", str(worktree), "branch", "--show-current"], 10)
    if branch_result.exit_code != 0:
        raise RuntimeError(f"failed to read scratch branch for {actor}")
    diff_result = runner(["git", "-C", str(worktree), "diff", "--binary", "HEAD"], 30)
    if diff_result.exit_code != 0:
        raise RuntimeError(f"failed to capture tracked diff for {actor}")
    tracked_diff = store.write_payload(
        f"{snapshot_root}/tracked.diff",
        diff_result.stdout,
    )
    if byte_ceiling is None:
        configured_ceiling = store.session.get("config", {}).get(
            "snapshot_byte_ceiling"
        )
        byte_ceiling = (
            int(configured_ceiling) if configured_ceiling is not None else None
        )

    untracked_result = runner(
        [
            "git",
            "-C",
            str(worktree),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        30,
    )
    if untracked_result.exit_code != 0:
        raise RuntimeError(f"failed to list untracked files for {actor}")

    untracked: list[dict[str, Any]] = []
    captured_bytes = 0
    omitted_bytes = 0
    for relative_path in sorted(
        path for path in untracked_result.stdout.split("\0") if path
    ):
        _validate_relative_payload_path(relative_path)
        source = worktree / relative_path
        data = source.read_bytes()
        entry: dict[str, Any] = {
            "path": relative_path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }
        if byte_ceiling is not None and captured_bytes + len(data) > byte_ceiling:
            entry["captured"] = False
            omitted_bytes += len(data)
        else:
            payload = store.write_payload(
                f"{snapshot_root}/untracked/{relative_path}",
                data,
            )
            entry["captured"] = True
            entry["payload_path"] = payload["path"]
            captured_bytes += payload["bytes"]
        untracked.append(entry)

    complete = omitted_bytes == 0

    snapshot_record = {
        "snapshot_id": snapshot_id,
        "actor": actor,
        "base_commit": store.session["base_commit"],
        "scratch_branch": branch_result.stdout.strip(),
        "complete": complete,
        "byte_ceiling": byte_ceiling,
        "captured_bytes": captured_bytes,
        "omitted_bytes": omitted_bytes,
        "tracked_diff": tracked_diff,
        "untracked": untracked,
    }
    snapshot_record_payload = store.write_payload(
        f"{snapshot_root}/snapshot.json",
        _json_text(snapshot_record),
    )
    event = store.append_event(
        "snapshot",
        {
            "actor": actor,
            "snapshot_id": snapshot_id,
            "base_commit": store.session["base_commit"],
            "scratch_branch": branch_result.stdout.strip(),
            "complete": complete,
            "payloads": {
                "snapshot_record": snapshot_record_payload,
                "tracked_diff": tracked_diff,
            },
        },
    )
    if not complete:
        store.append_event(
            "truncation",
            {
                "actor": "broker",
                "snapshot_id": snapshot_id,
                "byte_ceiling": byte_ceiling,
                "captured_bytes": captured_bytes,
                "omitted_bytes": omitted_bytes,
            },
        )
    store.render_views()

    return {
        "snapshot_id": snapshot_id,
        "actor": actor,
        "base_commit": store.session["base_commit"],
        "complete": complete,
        "snapshot_record_path": snapshot_record_payload["path"],
        "event_id": event["event_id"],
    }


def reconstruct_snapshot(
    *,
    session_dir: Path | str,
    snapshot_id: str,
    output_dir: Path | str,
    command_runner: Callable[[list[str], int], CommandResult] | None = None,
) -> Path:
    store = SessionStore.open(session_dir)
    runner = command_runner or _run_command
    output = Path(output_dir)
    if output.exists():
        raise ValueError(f"output directory already exists: {output}")
    snapshot_record = _read_json(
        store.session_dir / "snapshots" / snapshot_id / "snapshot.json"
    )
    if not snapshot_record.get("complete", False):
        raise ValueError(f"snapshot is incomplete: {snapshot_id}")

    clone = runner(
        ["git", "clone", "--quiet", str(store.session["repo_root"]), str(output)], 60
    )
    if clone.exit_code != 0:
        raise RuntimeError(
            f"failed to clone repo for snapshot reconstruction: {clone.stderr}"
        )
    checkout = runner(
        [
            "git",
            "-C",
            str(output),
            "checkout",
            "--quiet",
            snapshot_record["base_commit"],
        ],
        30,
    )
    if checkout.exit_code != 0:
        raise RuntimeError(f"failed to checkout snapshot base: {checkout.stderr}")

    diff_path = store.session_dir / snapshot_record["tracked_diff"]["path"]
    diff_text = diff_path.read_text(encoding="utf-8")
    if diff_text:
        apply_result = runner(["git", "-C", str(output), "apply", str(diff_path)], 30)
        if apply_result.exit_code != 0:
            raise RuntimeError(f"failed to apply tracked diff: {apply_result.stderr}")

    for item in snapshot_record["untracked"]:
        if not item.get("captured", True):
            continue
        _validate_relative_payload_path(item["path"])
        target = output / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((store.session_dir / item["payload_path"]).read_bytes())
    return output


def check_spec_ready(*, session_dir: Path | str) -> dict[str, Any]:
    store = SessionStore.open(session_dir)
    store.rebuild()
    state = _read_json(store.session_dir / "state.json")
    open_questions = state.get("open_questions", [])
    if open_questions:
        raise ValueError(f"unresolved question: {', '.join(open_questions)}")
    return state


def generate_spec(*, session_dir: Path | str, out_dir: Path | str) -> dict[str, Path]:
    check_spec_ready(session_dir=session_dir)
    store = SessionStore.open(session_dir)
    events = store._events()
    sections: dict[str, list[dict[str, str]]] = {
        "requirements": [],
        "design": [],
        "tasks": [],
    }
    deferred_dissent: list[dict[str, str]] = []

    for decision in _effective_decision_events(events):
        disposition = decision.get("disposition")
        decision_id = decision.get("decision_id", decision.get("event_id", "unknown"))
        if disposition == "rejected":
            continue
        if disposition == "deferred-dissent":
            payload_hash = _supporting_payload_hash(decision)
            if not payload_hash:
                raise ValueError(f"missing traceability for decision: {decision_id}")
            deferred_dissent.append(
                {
                    "text": decision.get("summary", ""),
                    "event_id": decision["event_id"],
                    "payload_hash": payload_hash,
                }
            )
            continue
        if disposition != "settled":
            continue
        outputs = decision.get("outputs")
        if not isinstance(outputs, dict) or not outputs:
            raise ValueError(f"unsupported decision: {decision_id}")
        unsupported_keys = sorted(set(outputs) - set(sections))
        if unsupported_keys:
            raise ValueError(
                f"unsupported decision output for {decision_id}: {', '.join(unsupported_keys)}"
            )
        payload_hash = _supporting_payload_hash(decision)
        if not payload_hash:
            raise ValueError(f"missing traceability for decision: {decision_id}")

        for section, items in outputs.items():
            if not isinstance(items, list) or not all(
                isinstance(item, str) for item in items
            ):
                raise ValueError(
                    f"unsupported decision output for {decision_id}: {section}"
                )
            for item in items:
                sections[section].append(
                    {
                        "text": item,
                        "event_id": decision["event_id"],
                        "payload_hash": payload_hash,
                    }
                )

    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "requirements.md": _render_generated_spec_file(
            "Requirements", sections["requirements"]
        ),
        "design.md": _render_generated_spec_file(
            "Design",
            sections["design"],
            deferred_dissent=deferred_dissent,
        ),
        "tasks.md": _render_generated_spec_file("Tasks", sections["tasks"]),
    }
    written: dict[str, Path] = {}
    for name, content in files.items():
        path = output / name
        path.write_text(content, encoding="utf-8")
        written[name] = path
    return written


def build_repo_guidance(repo_root: Path | str) -> list[dict[str, object]]:
    repo = Path(repo_root)
    entries = [
        ("AGENTS.md", "standing-rules", True),
        ("knowledge/glossary.md", "glossary", True),
        ("roadmap/specs/README.md", "spec-format", True),
        ("roadmap/ROADMAP.md", "board", True),
        ("features/README.md", "feature-conventions", False),
        ("knowledge/validation.md", "gate-inventory", False),
    ]
    guidance = [
        _guidance_entry(repo, path, role, required) for path, role, required in entries
    ]
    for path in _active_spec_paths(repo):
        guidance.append(_guidance_entry(repo, path, "active-spec", False))
    for path in _architecture_concept_paths(repo):
        guidance.append(_guidance_entry(repo, path, "architecture", False))
    return guidance


class SessionStore:
    """Append-only event and immutable payload writer for one session."""

    def __init__(self, session_dir: Path | str) -> None:
        self.session_dir = Path(session_dir)
        self.session_path = self.session_dir / "session.json"
        self.events_path = self.session_dir / "events.jsonl"
        if not self.session_path.is_file():
            raise FileNotFoundError(f"missing session.json: {self.session_path}")
        if not self.events_path.is_file():
            raise FileNotFoundError(f"missing events.jsonl: {self.events_path}")
        self.session = _read_json(self.session_path)
        self.session_id = self.session["session_id"]

    @classmethod
    def create(
        cls,
        *,
        session_dir: Path | str,
        session_id: str,
        repo_root: Path | str,
        base_commit: str,
        participants: list[str],
        config: dict[str, Any] | None = None,
    ) -> "SessionStore":
        path = Path(session_dir)
        path.mkdir(parents=True, exist_ok=True)
        session_path = path / "session.json"
        events_path = path / "events.jsonl"
        if session_path.exists() or events_path.exists():
            raise FileExistsError(f"session already exists: {path}")

        session = {
            "session_id": session_id,
            "repo_root": str(Path(repo_root)),
            "base_commit": base_commit,
            "participants": list(participants),
            "config": {"stall_rounds": 2, **(config or {})},
            "created_at": _utc_now(),
        }
        _write_json(session_path, session)
        events_path.write_text("", encoding="utf-8")
        return cls(path)

    @classmethod
    def open(cls, session_dir: Path | str) -> "SessionStore":
        return cls(session_dir)

    def write_payload(self, relative_path: str, content: str | bytes) -> dict[str, Any]:
        payload_path = self._payload_path(relative_path)
        data = content.encode("utf-8") if isinstance(content, str) else content
        if payload_path.exists():
            if payload_path.read_bytes() != data:
                raise ValueError(f"immutable payload exists: {relative_path}")
        else:
            payload_path.parent.mkdir(parents=True, exist_ok=True)
            payload_path.write_bytes(data)
        return {
            "path": relative_path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data),
        }

    def append_event(self, event_type: str, fields: dict[str, Any]) -> dict[str, Any]:
        if event_type not in KNOWN_EVENT_TYPES:
            raise ValueError(f"unknown event type: {event_type}")
        if not isinstance(fields, dict):
            raise TypeError("event fields must be a dict")
        reserved = RESERVED_EVENT_FIELDS.intersection(fields)
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ValueError(f"reserved event field supplied: {names}")
        supersedes = fields.get("supersedes")
        if supersedes is not None and supersedes not in self._event_ids():
            raise ValueError(f"supersedes unknown event_id: {supersedes}")

        event = {
            "event_id": self._next_event_id(),
            "type": event_type,
            "created_at": _utc_now(),
            "session_id": self.session_id,
            **fields,
        }
        line = json.dumps(event, sort_keys=True, separators=(",", ":"))
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(f"{line}\n")
        return event

    def render_views(self) -> dict[str, Path]:
        events = self._events()
        return self._write_views(_render_view_bytes(self.session_id, events))

    def rebuild(self) -> dict[str, Path]:
        events = self._events()
        self._validate_events(events)
        view_bytes = _render_view_bytes(self.session_id, events)
        for name, data in view_bytes.items():
            path = self.session_dir / name
            if path.exists() and path.read_bytes() != data:
                raise ValueError(f"tier 3 view differs: {name}")
        return self._write_views(view_bytes)

    def _write_views(self, view_bytes: dict[str, bytes]) -> dict[str, Path]:
        paths: dict[str, Path] = {}
        for name, data in view_bytes.items():
            path = self.session_dir / name
            path.write_bytes(data)
            paths[name] = path
        return paths

    def _validate_events(self, events: list[dict[str, Any]]) -> None:
        known_event_ids: set[str] = set()
        for event in events:
            event_id = event.get("event_id")
            if not event_id:
                raise ValueError("event missing event_id")
            event_type = event.get("type")
            if event_type not in KNOWN_EVENT_TYPES:
                raise ValueError(f"unknown event type: {event_type}")
            if event.get("supersedes") and event["supersedes"] not in known_event_ids:
                raise ValueError(f"supersedes unknown event_id: {event['supersedes']}")
            if event_type == "decision":
                disposition = event.get("disposition")
                if disposition not in VALID_DECISION_DISPOSITIONS:
                    decision_id = event.get("decision_id", event_id)
                    raise ValueError(
                        f"invalid disposition for {decision_id}: {disposition}"
                    )
            for payload in _iter_payload_refs(event.get("payloads")):
                self._validate_payload_ref(payload)
            known_event_ids.add(event_id)

    def _validate_payload_ref(self, payload: dict[str, Any]) -> None:
        relative_path = payload.get("path")
        expected_hash = payload.get("sha256")
        if not relative_path or not expected_hash:
            raise ValueError(f"payload reference missing path or sha256: {payload}")
        payload_path = self._payload_path(relative_path)
        if not payload_path.exists():
            raise ValueError(f"missing payload: {relative_path}")
        actual_hash = hashlib.sha256(payload_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"payload hash mismatch: {relative_path}")

    def _payload_path(self, relative_path: str) -> Path:
        path = PurePosixPath(relative_path)
        if path.is_absolute() or not path.parts or ".." in path.parts:
            raise ValueError(
                f"payload path must stay within the session: {relative_path}"
            )
        return self.session_dir / Path(*path.parts)

    def _events(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        with self.events_path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid events.jsonl at line {line_number}"
                    ) from exc
        return events

    def _event_ids(self) -> set[str]:
        return {event["event_id"] for event in self._events()}

    def _next_event_id(self) -> str:
        max_number = 0
        for event in self._events():
            event_id = event.get("event_id", "")
            if isinstance(event_id, str) and event_id.startswith("e"):
                try:
                    max_number = max(max_number, int(event_id[1:]))
                except ValueError:
                    continue
        return f"e{max_number + 1:06d}"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _read_manifest(
    repo_root: Path, failures: list[dict[str, str]]
) -> dict[str, Any] | None:
    path = repo_root / ".foundry/manifest.json"
    if not path.is_file():
        failures.append(
            {
                "check": "manifest",
                "command": ".foundry/manifest.json",
                "message": ".foundry/manifest.json missing",
            }
        )
        return None
    try:
        return _read_json(path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(
            {
                "check": "manifest",
                "command": ".foundry/manifest.json",
                "message": f".foundry/manifest.json invalid: {exc}",
            }
        )
        return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        _json_text(value),
        encoding="utf-8",
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def _run_command(command: list[str], timeout_s: int) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or "timed out")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _run_command_with_input(
    command: list[str],
    *,
    cwd: Path,
    stdin: str,
    timeout_s: int,
) -> CommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=stdin,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(124, exc.stdout or "", exc.stderr or "timed out")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def _materialize_live_smoke_prompt(
    *,
    repo: Path,
    session_id: str,
    prompt_file: Path | str | None,
    prompt_text: str | None,
) -> Path:
    if prompt_file is not None:
        return Path(prompt_file)
    prompt_dir = repo / ".foundry/tmp/harness-deliberation/live-smoke-prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompt_dir / f"{session_id}.md"
    prompt_path.write_text(prompt_text or DEFAULT_LIVE_SMOKE_PROMPT, encoding="utf-8")
    return prompt_path


LIVE_SMOKE_BOUNDARY = (
    "# Live Smoke Boundary\n"
    "This is an opt-in smoke test. Do not edit files or run tools. "
    "Reply with one concise sentence confirming that you read the prompt.\n"
)

ROUND_OUTPUT_CONTRACT = (
    "# Output Contract\n"
    "Return your final answer as peer-readable Markdown with these sections:\n"
    "## Position\n"
    "## Answers To Open Questions\n"
    "## Risks\n"
    "## Challenges To Peer Finals\n"
    "## Recommended Changes\n"
    "If a section has nothing yet (for example no peer finals on the first turn), "
    'write "none". Do not edit files; you have read-only tools for grounding.\n'
)


def _live_participant_runner(
    repo: Path,
    timeout_s: int,
    claude_budget_usd: str,
) -> Callable[[str, Path, Path], ParticipantResult]:
    def runner(actor: str, prompt_path: Path, raw_path: Path) -> ParticipantResult:
        prompt_text = prompt_path.read_text(encoding="utf-8").rstrip()
        return _execute_harness_turn(
            actor=actor,
            repo=repo,
            prompt_text=f"{prompt_text}\n\n{LIVE_SMOKE_BOUNDARY}",
            raw_path=raw_path,
            timeout_s=timeout_s,
            claude_budget_usd=claude_budget_usd,
            allowed_tools=None,
        )

    return runner


def _round_participant_runner(
    repo: Path,
    timeout_s: int,
    claude_budget_usd: str,
) -> Callable[[str, Path, Path], ParticipantResult]:
    def runner(actor: str, prompt_path: Path, raw_path: Path) -> ParticipantResult:
        prompt_text = prompt_path.read_text(encoding="utf-8").rstrip()
        return _execute_harness_turn(
            actor=actor,
            repo=repo,
            prompt_text=f"{prompt_text}\n\n{ROUND_OUTPUT_CONTRACT}",
            raw_path=raw_path,
            timeout_s=timeout_s,
            claude_budget_usd=claude_budget_usd,
            allowed_tools="Read,Grep,Glob",
        )

    return runner


def _execute_harness_turn(
    *,
    actor: str,
    repo: Path,
    prompt_text: str,
    raw_path: Path,
    timeout_s: int,
    claude_budget_usd: str,
    allowed_tools: str | None,
) -> ParticipantResult:
    """Run one harness turn read-only with the prompt on stdin.

    The prompt is never placed on argv, so the recorded command vector cannot leak
    it; the raw log references the prompt by SHA-256 only.
    """
    if actor == "codex":
        final_path = raw_path.with_name("codex-final.txt")
        command = [
            "codex",
            "exec",
            "--cd",
            str(repo),
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--output-last-message",
            str(final_path),
            "-",
        ]
        result = _run_command_with_input(
            command, cwd=repo, stdin=prompt_text, timeout_s=timeout_s
        )
        raw = _format_raw_turn(command, result, prompt_text)
        _classify_turn_failure(actor, result)
        final = (
            final_path.read_text(encoding="utf-8")
            if final_path.is_file()
            else result.stdout
        )
        return ParticipantResult(final=_ensure_trailing_newline(final.strip()), raw=raw)
    if actor == "claude-code":
        command = [
            "claude",
            "-p",
            "--output-format",
            "text",
            "--max-budget-usd",
            claude_budget_usd,
            "--permission-mode",
            "dontAsk",
            "--no-session-persistence",
        ]
        if allowed_tools:
            command += ["--allowedTools", allowed_tools]
        else:
            command += ["--tools", ""]
        result = _run_command_with_input(
            command, cwd=repo, stdin=prompt_text, timeout_s=timeout_s
        )
        raw = _format_raw_turn(command, result, prompt_text)
        _classify_turn_failure(actor, result)
        return ParticipantResult(
            final=_ensure_trailing_newline(result.stdout.strip()), raw=raw
        )
    raise ValueError(f"unsupported participant: {actor}")


def _classify_turn_failure(actor: str, result: CommandResult) -> None:
    if result.exit_code == 0:
        return
    detail = f"{result.stdout}\n{result.stderr}".strip()
    lower = detail.lower()
    if "usage limit" in lower or "quota" in lower or "usage cap" in lower:
        raise ParticipantLimited(actor=actor, category="usage-limited", detail=detail)
    if "rate limit" in lower or "rate-limited" in lower:
        raise ParticipantLimited(actor=actor, category="rate-limited", detail=detail)
    raise ParticipantFailed(actor=actor, exit_code=result.exit_code, detail=detail)


def _format_raw_turn(
    command: list[str], result: CommandResult, prompt_text: str
) -> str:
    return _json_text(
        {
            "command": command,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        }
    )


def _ensure_trailing_newline(text: str) -> str:
    return text.rstrip() + "\n"


def _git_status_snapshot(
    repo: Path,
    command_runner: Callable[[list[str], int], CommandResult],
) -> list[str]:
    result = command_runner(
        ["git", "-C", str(repo), "status", "--porcelain=v1", "--untracked-files=all"],
        30,
    )
    if result.exit_code != 0:
        raise RuntimeError(f"failed to read git status: {result.stderr}")
    return [
        line
        for line in result.stdout.splitlines()
        if ".foundry/tmp/" not in line and not line.endswith(".foundry/tmp")
    ]


def _status_diff(before: list[str], after: list[str]) -> str:
    return "\n".join(
        [
            "before:",
            *[f"  {line}" for line in before],
            "after:",
            *[f"  {line}" for line in after],
        ]
    )


def _git_head(
    repo_root: Path,
    command_runner: Callable[[list[str], int], CommandResult],
) -> str:
    result = command_runner(
        ["git", "-C", str(repo_root), "rev-parse", "--short", "HEAD"], 10
    )
    if result.exit_code != 0:
        raise RuntimeError("failed to read git HEAD")
    return result.stdout.strip()


def _check_harness_statuses(
    repo_root: Path, harnesses: list[str]
) -> list[dict[str, object]]:
    status_path = Path(__file__).with_name("harness-status.py")
    spec = importlib.util.spec_from_file_location("harness_status", status_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load {status_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.check_selected_harnesses(repo_root=repo_root, harnesses=harnesses)


def _render_view_bytes(
    session_id: str, events: list[dict[str, Any]]
) -> dict[str, bytes]:
    state = _project_state(session_id, events)
    return {
        "state.json": _json_text(state).encode("utf-8"),
        "state.md": _render_state_md(state).encode("utf-8"),
        "transcript.md": _render_transcript_md(session_id, events).encode("utf-8"),
    }


def _next_round_id(events: list[dict[str, Any]]) -> str:
    round_numbers = []
    for event in events:
        round_id = event.get("round_id")
        if isinstance(round_id, str) and round_id.startswith("r"):
            try:
                round_numbers.append(int(round_id[1:]))
            except ValueError:
                continue
    return f"r{(max(round_numbers) if round_numbers else 0) + 1:04d}"


def _round_participants(round_id: str) -> list[str]:
    try:
        number = int(round_id[1:])
    except ValueError:
        number = 1
    if number % 2 == 0:
        return ["claude-code", "codex"]
    return ["codex", "claude-code"]


def _resume_round(events: list[dict[str, Any]]) -> tuple[str, list[str], bool]:
    """Pick the round to run: resume the latest incomplete one, else start a new one.

    Returns (round_id, participants_still_needing_a_final, is_new_round). A round is
    "started" once it has a repo_guidance event; it is complete when every
    participant has a participant_final for it.
    """
    started_rounds: list[str] = []
    for event in events:
        if event.get("type") == "repo_guidance":
            round_id = event.get("round_id")
            if isinstance(round_id, str) and round_id not in started_rounds:
                started_rounds.append(round_id)
    if started_rounds:
        latest = started_rounds[-1]
        finals = {
            event.get("actor")
            for event in events
            if event.get("type") == "participant_final"
            and event.get("round_id") == latest
        }
        remaining = [
            actor for actor in _round_participants(latest) if actor not in finals
        ]
        if remaining:
            return latest, remaining, False
    new_round = _next_round_id(events)
    return new_round, _round_participants(new_round), True


def _guidance_for_round(
    events: list[dict[str, Any]], round_id: str
) -> list[dict[str, object]]:
    for event in events:
        if event.get("type") == "repo_guidance" and event.get("round_id") == round_id:
            return event.get("guidance", [])
    return []


def _peer_finals_for_round(store: SessionStore, round_id: str) -> list[dict[str, str]]:
    peer_finals: list[dict[str, str]] = []
    for event in store._events():
        if (
            event.get("type") != "participant_final"
            or event.get("round_id") != round_id
        ):
            continue
        final_payload = event.get("payloads", {}).get("final", {})
        path = final_payload.get("path")
        if not path:
            continue
        content = (store.session_dir / path).read_text(encoding="utf-8")
        peer_finals.append(
            {"actor": event.get("actor"), "path": path, "content": content}
        )
    return peer_finals


def _next_turn_id(events: list[dict[str, Any]], actor: str) -> str:
    turn_events = {
        "participant_final",
        "participant_failed",
        "participant_limited",
    }
    next_number = 1 + sum(1 for event in events if event.get("type") in turn_events)
    slug = TURN_SLUG_BY_HARNESS.get(actor, actor.replace("-code", ""))
    return f"{next_number:04d}-{slug}"


def _maybe_emit_stall(store: SessionStore, round_id: str) -> None:
    events = store._events()
    threshold = int(store.session.get("config", {}).get("stall_rounds", 2))
    if threshold <= 0:
        return

    reset_index = -1
    for index, event in enumerate(events):
        if event.get("type") in PROGRESS_EVENT_TYPES or event.get("type") == "stall":
            reset_index = index

    recent_rounds: list[str] = []
    for event in events[reset_index + 1 :]:
        if event.get("type") != "participant_final":
            continue
        event_round = event.get("round_id")
        if isinstance(event_round, str) and event_round not in recent_rounds:
            recent_rounds.append(event_round)

    if len(recent_rounds) < threshold or recent_rounds[-1] != round_id:
        return

    state = _project_state(store.session_id, events)
    store.append_event(
        "stall",
        {
            "actor": "broker",
            "round_id": round_id,
            "stall_rounds": threshold,
            "last_progress_hash": state["last_progress_hash"],
        },
    )


def _current_state_md(store: SessionStore) -> str:
    events = store._events()
    state = _project_state(store.session_id, events)
    return _render_state_md(state)


def _render_participant_prompt(
    *,
    session_id: str,
    actor: str,
    round_id: str,
    mediator_prompt: str,
    guidance: list[dict[str, object]],
    state_md: str,
    peer_finals: list[dict[str, str]],
) -> str:
    lines = [
        f"# Harness Deliberation Turn - {actor}",
        "",
        f"- Session: {session_id}",
        f"- Round: {round_id}",
        "",
        "# Mediator Prompt",
        "",
        mediator_prompt.rstrip(),
        "",
        "# Repo Guidance",
    ]
    for item in guidance:
        required = "required" if item["required"] else "optional"
        exists = "exists" if item["exists"] else "missing"
        lines.append(f"- {item['path']} ({item['role']}, {required}, {exists})")

    lines.extend(["", "# Compact State", "", state_md.rstrip(), "", "# Peer Finals"])
    if peer_finals:
        for final in peer_finals:
            lines.extend(
                [
                    f"## {final['actor']} - {final['path']}",
                    final["content"].rstrip(),
                    "",
                ]
            )
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def _project_state(session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    questions: dict[str, dict[str, Any]] = {}
    decisions_by_event: dict[str, dict[str, Any]] = {}
    superseded_events: set[str] = set()
    rounds: dict[str, list[str]] = {}
    snapshots: dict[str, dict[str, Any]] = {}

    for event in events:
        event_type = event.get("type")
        if event_type == "question" and event.get("question_id"):
            question_id = event["question_id"]
            questions[question_id] = _event_record(
                event,
                ["event_id", "actor", "question_id", "text", "supersedes"],
            )
        elif event_type == "decision" and event.get("decision_id"):
            decision = _event_record(
                event,
                [
                    "event_id",
                    "actor",
                    "decision_id",
                    "question_id",
                    "disposition",
                    "summary",
                    "supersedes",
                    "outputs",
                    "payloads",
                ],
            )
            decisions_by_event[event["event_id"]] = decision
            if event.get("supersedes"):
                superseded_events.add(event["supersedes"])
        elif event_type == "participant_final":
            round_id = event.get("round_id")
            turn_id = event.get("turn_id")
            if round_id and turn_id:
                rounds.setdefault(round_id, [])
                if turn_id not in rounds[round_id]:
                    rounds[round_id].append(turn_id)
        elif event_type == "snapshot" and event.get("snapshot_id"):
            snapshot_id = event["snapshot_id"]
            snapshots[snapshot_id] = _event_record(
                event,
                ["event_id", "actor", "snapshot_id", "complete", "payloads"],
            )

    decisions = {
        decision["decision_id"]: decision
        for event_id, decision in sorted(decisions_by_event.items())
        if event_id not in superseded_events
    }
    closed_questions = {
        decision["question_id"]
        for decision in decisions.values()
        if decision.get("question_id") and decision.get("disposition")
    }
    open_questions = sorted(
        question_id for question_id in questions if question_id not in closed_questions
    )
    deferred_dissent = sorted(
        decision_id
        for decision_id, decision in decisions.items()
        if decision.get("disposition") == "deferred-dissent"
    )

    progress_source = {
        "questions": questions,
        "decisions": decisions,
        "open_questions": open_questions,
        "deferred_dissent": deferred_dissent,
        "snapshots": snapshots,
    }

    return {
        "session_id": session_id,
        "event_count": len(events),
        "questions": questions,
        "decisions": decisions,
        "open_questions": open_questions,
        "deferred_dissent": deferred_dissent,
        "snapshots": snapshots,
        "rounds": {round_id: rounds[round_id] for round_id in sorted(rounds)},
        "last_progress_hash": _stable_hash(progress_source),
    }


def _event_record(event: dict[str, Any], keys: list[str]) -> dict[str, Any]:
    return {key: event[key] for key in keys if key in event}


def _effective_decision_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decisions_by_event: dict[str, dict[str, Any]] = {}
    superseded_events: set[str] = set()
    for event in events:
        if event.get("type") != "decision" or not event.get("event_id"):
            continue
        decisions_by_event[event["event_id"]] = event
        if event.get("supersedes"):
            superseded_events.add(event["supersedes"])
    return [
        event
        for event_id, event in sorted(decisions_by_event.items())
        if event_id not in superseded_events
    ]


def _supporting_payload_hash(event: dict[str, Any]) -> str | None:
    payloads = list(_iter_payload_refs(event.get("payloads")))
    if not payloads:
        return None
    return str(payloads[0]["sha256"])


def _render_generated_spec_file(
    title: str,
    entries: list[dict[str, str]],
    *,
    deferred_dissent: list[dict[str, str]] | None = None,
) -> str:
    lines = [f"# {title} — generated", ""]
    if not entries:
        lines.append("_No settled generated content._")
    for entry in entries:
        lines.append(f"- {entry['text']}")
        lines.append(
            f"  Trace: decision {entry['event_id']}; payload {entry['payload_hash']}"
        )
    if deferred_dissent:
        lines.extend(["", "## Deferred Dissent"])
        for entry in deferred_dissent:
            lines.append(f"- {entry['text']}")
            lines.append(
                f"  Trace: decision {entry['event_id']}; payload {entry['payload_hash']}"
            )
    return "\n".join(lines) + "\n"


def _branch_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "session"


def _next_snapshot_number(events: list[dict[str, Any]]) -> int:
    numbers = []
    for event in events:
        snapshot_id = event.get("snapshot_id")
        if isinstance(snapshot_id, str):
            prefix = snapshot_id.split("-", 1)[0]
            try:
                numbers.append(int(prefix))
            except ValueError:
                continue
    return (max(numbers) if numbers else 0) + 1


def _validate_relative_payload_path(relative_path: str) -> None:
    path = PurePosixPath(relative_path)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"path must stay within snapshot: {relative_path}")


def _known_question_ids(events: list[dict[str, Any]]) -> set[str]:
    return {
        event["question_id"]
        for event in events
        if event.get("type") == "question" and event.get("question_id")
    }


def _decision_event_ids(events: list[dict[str, Any]]) -> set[str]:
    return {
        event["event_id"]
        for event in events
        if event.get("type") == "decision" and event.get("event_id")
    }


def _required_string(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"missing required string field: {key}")
    return result


def _guidance_entry(
    repo_root: Path,
    relative_path: str,
    role: str,
    required: bool,
) -> dict[str, object]:
    path = repo_root / relative_path
    entry: dict[str, object] = {
        "path": relative_path,
        "role": role,
        "required": required,
        "exists": path.is_file(),
    }
    if path.is_file():
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return entry


def _active_spec_paths(repo_root: Path) -> list[str]:
    specs_dir = repo_root / "roadmap/specs"
    if not specs_dir.is_dir():
        return []
    paths = []
    for name in ["requirements.md", "design.md", "tasks.md"]:
        paths.extend(
            str(path.relative_to(repo_root))
            for path in sorted(specs_dir.glob(f"*/{name}"))
        )
    return sorted(paths)


def _architecture_concept_paths(repo_root: Path) -> list[str]:
    knowledge_dir = repo_root / "knowledge"
    if not knowledge_dir.is_dir():
        return []
    paths = []
    for path in sorted(knowledge_dir.rglob("*.md")):
        try:
            head = path.read_text(encoding="utf-8").split("---", 2)
        except UnicodeDecodeError:
            continue
        frontmatter = head[1] if len(head) >= 3 else ""
        if re.search(r"(?m)^type:\s*architecture\s*$", frontmatter):
            paths.append(str(path.relative_to(repo_root)))
    return paths


def _iter_payload_refs(value: Any):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
            return
        for child in value.values():
            yield from _iter_payload_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_payload_refs(child)


def _render_state_md(state: dict[str, Any]) -> str:
    lines = [
        f"# State - {state['session_id']}",
        "",
        f"- Events: {state['event_count']}",
        f"- Open questions: {_comma_list(state['open_questions'])}",
        f"- Deferred dissent: {_comma_list(state['deferred_dissent'])}",
        f"- Last progress hash: {state['last_progress_hash']}",
        "",
        "## Questions",
    ]
    if state["questions"]:
        for question_id in sorted(state["questions"]):
            question = state["questions"][question_id]
            lines.append(f"- {question_id}: {question.get('text', '')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Decisions"])
    if state["decisions"]:
        for decision_id in sorted(state["decisions"]):
            decision = state["decisions"][decision_id]
            line = (
                f"- {decision_id}: {decision.get('disposition', '')}"
                f" for {decision.get('question_id', 'unknown-question')}"
            )
            if decision.get("supersedes"):
                line += f" (supersedes {decision['supersedes']})"
            if decision.get("summary"):
                line += f" - {decision['summary']}"
            lines.append(line)
    else:
        lines.append("- none")

    lines.extend(["", "## Rounds"])
    if state["rounds"]:
        for round_id in sorted(state["rounds"]):
            lines.append(f"- {round_id}: {', '.join(state['rounds'][round_id])}")
    else:
        lines.append("- none")

    lines.extend(["", "## Snapshots"])
    if state["snapshots"]:
        for snapshot_id in sorted(state["snapshots"]):
            snapshot = state["snapshots"][snapshot_id]
            complete = snapshot.get("complete", False)
            lines.append(f"- {snapshot_id}: complete={str(complete).lower()}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def _render_transcript_md(session_id: str, events: list[dict[str, Any]]) -> str:
    lines = [f"# Transcript - {session_id}", ""]
    for event in events:
        parts = [f"- {event['event_id']} `{event['type']}`"]
        for key in ["actor", "round_id", "turn_id"]:
            if event.get(key):
                parts.append(f"{key.replace('_id', '')}={event[key]}")
        lines.append(" ".join(parts))
        for name, payload in sorted((event.get("payloads") or {}).items()):
            if isinstance(payload, dict) and payload.get("path"):
                lines.append(f"  - {name}: {payload['path']}")
    return "\n".join(lines) + "\n"


def _comma_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"


def _stable_hash(value: dict[str, Any]) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start")
    start_parser.add_argument("--prompt", required=True)
    start_parser.add_argument("--session", required=True)
    start_parser.add_argument("--repo", default=".")
    start_parser.add_argument("--attach", action="store_true")
    start_parser.add_argument("--dry-run", action="store_true")

    rebuild_parser = subparsers.add_parser("rebuild")
    rebuild_parser.add_argument("--session-dir", required=True)

    decide_parser = subparsers.add_parser("decide")
    decide_parser.add_argument("--session-dir", required=True)
    decide_parser.add_argument("--file", required=True)

    spec_parser = subparsers.add_parser("spec")
    spec_parser.add_argument("--session-dir", required=True)
    spec_parser.add_argument("--out", required=True)

    live_smoke_parser = subparsers.add_parser("live-smoke")
    live_smoke_parser.add_argument("--repo", default=".")
    live_smoke_parser.add_argument("--session", required=True)
    live_smoke_parser.add_argument("--prompt")
    live_smoke_parser.add_argument("--timeout-s", type=int, default=180)
    live_smoke_parser.add_argument(
        "--claude-budget-usd",
        default=DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD,
    )

    round_parser = subparsers.add_parser("round")
    round_parser.add_argument("--session-dir", required=True)
    round_parser.add_argument("--timeout-s", type=int, default=300)
    round_parser.add_argument(
        "--budget-usd",
        default=DEFAULT_CLAUDE_LIVE_SMOKE_BUDGET_USD,
    )

    args = parser.parse_args(argv)
    if args.command == "start":
        try:
            result = start_session(
                repo_root=args.repo,
                prompt_file=args.prompt,
                session_id=args.session,
                attach=args.attach,
                is_interactive=True,
                run_tmux=not args.dry_run,
            )
        except Exception as exc:
            print(str(exc))
            return 1
        if args.dry_run:
            for command in result.tmux_commands:
                print(" ".join(command))
        if args.attach:
            print(f"attach with: {result.attach_command}")
        else:
            print(f"session: {result.session_dir}")
        return 0

    if args.command == "rebuild":
        try:
            SessionStore.open(args.session_dir).rebuild()
        except Exception as exc:
            print(str(exc))
            return 1
        print("rebuild: PASS")
        return 0

    if args.command == "decide":
        try:
            apply_decision_file(
                session_dir=args.session_dir,
                decision_file=args.file,
            )
        except Exception as exc:
            print(str(exc))
            return 1
        print("decide: PASS")
        return 0

    if args.command == "spec":
        try:
            generate_spec(session_dir=args.session_dir, out_dir=args.out)
        except Exception as exc:
            print(str(exc))
            return 1
        print(f"spec: WROTE {args.out}")
        print("per-turn repo guidance is not a final spec-review pass")
        return 0

    if args.command == "live-smoke":
        try:
            result = run_live_smoke(
                repo_root=args.repo,
                session_id=args.session,
                prompt_file=args.prompt,
                timeout_s=args.timeout_s,
                claude_budget_usd=args.claude_budget_usd,
            )
        except Exception as exc:
            print(str(exc))
            return 1
        print("live-smoke: PASS")
        print(f"session: {result['session_dir']}")
        for final in result["finals"]:
            print(f"{final['actor']} final: {final['path']}")
        print("worktree: unchanged")
        return 0

    if args.command == "round":
        try:
            store = SessionStore.open(args.session_dir)
            if store.session_id != Path(args.session_dir).name:
                raise ValueError(
                    f"session_id {store.session_id!r} does not match directory "
                    f"{Path(args.session_dir).name!r}"
                )
            repo = Path(store.session["repo_root"])
            run_round(
                session_dir=args.session_dir,
                participant_runner=_round_participant_runner(
                    repo, args.timeout_s, args.budget_usd
                ),
            )
        except Exception as exc:
            print(str(exc))
            return 1
        print("round: PASS")
        print(f"session: {args.session_dir}")
        return 0

    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
