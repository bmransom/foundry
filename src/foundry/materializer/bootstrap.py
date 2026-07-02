"""`foundry bootstrap` (design D6, US-7): interview (judgment) -> deterministic
materialize -> manifest stamp -> gate-suite verify.

The interview is the only judgment step: it compiles the v1 interview questions into a
prompt, runs them through the routed harness via `adapters.headless`, and parses a JSON
answers block from the reply. Everything after is deterministic code over an `Answers`
value (AC-7.2), so materialized files never depend on an LLM copying correctly.

Materialize is idempotent (AC-7.1): every write is byte-compared first, so a re-run over a
pristine install writes nothing; an existing file that differs is reported and skipped,
never overwritten (v1's merge-additively-or-skip rule). Stdlib only.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from foundry import __version__
from foundry.config import Route

CONVENTION_VERSION = 5
DEFAULT_REPO_URL = "https://github.com/bmransom/foundry"
# Aligned to __version__ (no "v" prefix) so doctor's config check — which compares the
# pin to the running CLI version verbatim — is clean on a fresh bootstrap.
DEFAULT_PIN = __version__
DEFAULT_HARNESSES = ("claude-code", "codex")

# `# foundry-template: <name> v<N>` in any comment host (sh, //, JSON "//": "...").
_MARKER_RE = re.compile(r"foundry-template:\s*(\S+)\s+v(\d+)")
# A ```json ... ``` fenced block in an interview reply.
_ANSWERS_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)

_PRE_PUSH_REL = ".githooks/pre-push"
_SITE_JSON_REL = "knowledge/.vitepress/site.json"


class BootstrapError(Exception):
    """An answers file, interview reply, or template marker was unusable."""


@dataclass(frozen=True)
class Answers:
    """The interview's output as data — everything materialize needs (AC-7.2)."""

    repo_name: str
    description: str = ""
    harnesses: tuple[str, ...] = DEFAULT_HARNESSES
    vocabulary: tuple[str, ...] = ()
    gate_test: str | None = None
    gate_commands: tuple[str, ...] = ()
    pin: str = DEFAULT_PIN
    repo_url: str = DEFAULT_REPO_URL

    @classmethod
    def from_dict(cls, data: dict) -> "Answers":
        if not isinstance(data, dict) or not data.get("repo_name"):
            raise BootstrapError("answers must be an object with a non-empty 'repo_name'")
        return cls(
            repo_name=data["repo_name"],
            description=data.get("description", ""),
            harnesses=tuple(data.get("harnesses", DEFAULT_HARNESSES)),
            vocabulary=tuple(data.get("vocabulary", ())),
            gate_test=data.get("gate_test"),
            gate_commands=tuple(data.get("gate_commands", ())),
            pin=data.get("pin", DEFAULT_PIN),
            repo_url=data.get("repo_url", DEFAULT_REPO_URL),
        )

    @classmethod
    def from_json_file(cls, path: Path | str) -> "Answers":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise BootstrapError(f"could not read answers file {path}: {e}") from e
        return cls.from_dict(data)


@dataclass
class BootstrapResult:
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    manifest: dict = field(default_factory=dict)


# --- Interview (judgment seam) --------------------------------------------------------

INTERVIEW_QUESTIONS = (
    "Target harness(es) — which AI coding tools run this setup: claude-code, codex, "
    "or both (default both).",
    "A one-paragraph project description.",
    "5-10 domain terms (and the wrong names that keep appearing) to seed the glossary.",
    "Vocabulary polarity: exclude outside domain vocabulary (a neutral engine) or "
    "embrace it (a product)?",
    "Is there an API surface (HTTP, RPC, public library API)?",
    "The build-stage gate: the command that runs the repo's tests.",
    "Any additional gate commands the team already runs (heavy checks, linters).",
    "Will parallel agents work in this repo on one machine?",
    "The first epic — the milestone that heads the board.",
)

_ANSWERS_SCHEMA = (
    '{"repo_name": "<slug>", "description": "<one paragraph>", '
    '"harnesses": ["claude-code", "codex"], "vocabulary": ["<term>", ...], '
    '"gate_test": "<test command or null>", "gate_commands": ["<command>", ...], '
    '"repo_url": "<git remote url>"}'
)


def compile_interview_prompt(repo_root: Path | str) -> str:
    numbered = "\n".join(f"{i}. {q}" for i, q in enumerate(INTERVIEW_QUESTIONS, 1))
    return (
        f"Interview the maintainer to bootstrap the foundry engineering setup into "
        f"{repo_root}. Inspect the repo's stack first, then resolve each question:\n\n"
        f"{numbered}\n\n"
        "Reply with a single fenced ```json block carrying exactly this shape "
        "(omit unknown fields; harnesses defaults to both):\n"
        f"{_ANSWERS_SCHEMA}\n"
    )


def parse_answers_reply(text: str) -> Answers:
    match = _ANSWERS_BLOCK_RE.search(text)
    if not match:
        raise BootstrapError("interview reply carried no ```json answers block")
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise BootstrapError(f"interview answers block is not valid JSON: {e}") from e
    return Answers.from_dict(data)


def interview(adapter, route: Route, workspace: str, *, run=None) -> Answers:
    """Run the interview through the routed harness and parse its JSON answers block.

    `run` is the injectable subprocess runner threaded to `adapters.headless`, so the
    seam is unit-testable with a fake harness runner (no live call).
    """
    from foundry import adapters

    prompt_file = Path(workspace) / ".foundry" / "bootstrap-interview.md"
    prompt_file.parent.mkdir(parents=True, exist_ok=True)
    prompt_file.write_text(compile_interview_prompt(workspace), encoding="utf-8")
    result = adapters.headless(adapter, str(prompt_file), route, workspace, run=run)
    return parse_answers_reply(result.text)


# --- Deterministic materialize --------------------------------------------------------


def verbatim_root() -> Path:
    return Path(str(resources.files("foundry"))) / "templates" / "verbatim"


def seeds_root() -> Path:
    return Path(str(resources.files("foundry"))) / "templates" / "seeds"


def _parse_marker(text: str, rel: str) -> tuple[str, int]:
    match = _MARKER_RE.search(text)
    if not match:
        raise BootstrapError(f"verbatim template {rel} has no foundry-template marker")
    return match.group(1), int(match.group(2))


def _desired_mode(executable: bool) -> int:
    return 0o755 if executable else 0o644


def _write(path: Path, content: bytes, *, executable: bool, rel: str, result: BootstrapResult) -> None:
    """Write `content` at `path` unless it is already byte-identical (idempotent) or an
    existing file differs (skip + report, never overwrite)."""
    desired = _desired_mode(executable)
    if path.is_symlink() or path.exists():
        if path.is_file() and path.read_bytes() == content:
            if stat.S_IMODE(path.stat().st_mode) != desired:
                path.chmod(desired)
            return
        result.skipped.append(rel)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    path.chmod(desired)
    result.written.append(rel)


def _write_symlink(path: Path, target: str, rel: str, result: BootstrapResult) -> None:
    if path.is_symlink():
        if os.readlink(path) == target:
            return
        result.skipped.append(rel)
        return
    if path.exists():
        result.skipped.append(rel)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)
    result.written.append(rel)


def _pinned_pre_push(repo_url: str, pin: str) -> bytes:
    return (
        "#!/usr/bin/env bash\n"
        "# Pre-push gate; bypass once with `git push --no-verify`.\n"
        f'exec uvx --from "git+{repo_url}@{pin}" foundry gate\n'
    ).encode("utf-8")


def _render_config(answers: Answers) -> bytes:
    commands = ", ".join(f'"{c}"' for c in answers.gate_commands)
    lines = [
        "[foundry]",
        f'pin = "{answers.pin}"',
        f'repo_url = "{answers.repo_url}"',
        "",
        "[gate]",
    ]
    if answers.gate_test:
        lines.append(f'test = "{answers.gate_test}"')
    lines.append(f"commands = [{commands}]")
    lines.append("")
    return ("\n".join(lines)).encode("utf-8")


def _render_agents_md(answers: Answers) -> bytes:
    pinned = f'uvx --from "git+{answers.repo_url}@{answers.pin}" foundry gate'
    command_lines = []
    if answers.gate_test:
        command_lines.append(f"{answers.gate_test}          # build gate: the repo's tests")
    for cmd in answers.gate_commands:
        command_lines.append(f"{cmd}          # verify-stage gate addition")
    if not command_lines:
        command_lines.append("# add the repo's gate commands to .foundry/config.toml")
    commands_block = "\n".join(command_lines)
    vocab = ", ".join(answers.vocabulary) if answers.vocabulary else "(seed in knowledge/glossary.md)"
    desc = answers.description or "(describe the repo here)"

    return (
        f"# AGENTS.md — {answers.repo_name}\n\n"
        f"{desc}\n\n"
        "This skeleton is deterministic; refine the prose interactively. The board is\n"
        "`roadmap/ROADMAP.md`, per-feature detail in `roadmap/specs/<feature>/`, vocabulary\n"
        "in `knowledge/glossary.md`.\n\n"
        "## Commands\n\n"
        "```bash\n"
        f"{commands_block}\n"
        "```\n\n"
        "The gate runs at the pinned foundry version from the pre-push hook and CI:\n\n"
        "```sh\n"
        f"{pinned}\n"
        "```\n\n"
        "Route git hooks through `.githooks/` once per clone:\n\n"
        "```sh\n"
        "git config core.hooksPath .githooks\n"
        "```\n\n"
        "## Boundaries\n\n"
        "**Always**\n"
        "- Keep every convention in repo files (`AGENTS.md`, board, glossary, gate config)\n"
        "  so any harness reads the repo with no foundry install.\n"
        "- Make surgical changes; never claim a change is tested unless it was.\n\n"
        f"Domain vocabulary: {vocab}.\n\n"
        "## Task tracking\n\n"
        "`roadmap/ROADMAP.md` is the board — the single source of truth for cross-spec\n"
        "status. Claim a card by creating its `card/<id>` branch; a card is Done when its\n"
        "branch merges to the default branch with the gate green.\n"
    ).encode("utf-8")


def _fill_site_json(source: bytes, answers: Answers) -> bytes:
    data = json.loads(source.decode("utf-8"))
    data["title"] = answers.repo_name
    data["description"] = answers.description or data.get("description", "")
    return (json.dumps(data, indent=2) + "\n").encode("utf-8")


def _copy_verbatim(repo_root: Path, answers: Answers, result: BootstrapResult) -> dict:
    """Copy every verbatim file byte-exact (exec bits restored from the package path),
    substituting the pinned pre-push for the vendored one, and return the manifest files
    map (per-file template name, marker version, sha256)."""
    root = verbatim_root()
    files: dict[str, dict] = {}
    for source in sorted(root.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        rel = str(source.relative_to(root))
        raw = source.read_bytes()
        name, version = _parse_marker(raw.decode("utf-8", "replace"), rel)
        executable = bool(source.stat().st_mode & stat.S_IXUSR)

        if rel == _PRE_PUSH_REL:
            content = _pinned_pre_push(answers.repo_url, answers.pin)
            executable = True
        else:
            content = raw

        _write(repo_root / rel, content, executable=executable, rel=rel, result=result)
        files[rel] = {
            "template": name,
            "version": version,
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return files


def _copy_seeds(repo_root: Path, answers: Answers, result: BootstrapResult) -> None:
    """Copy seed files, filling what Answers covers (site.json title/description); the
    rest stays as seeded (judgment content the repo will own)."""
    root = seeds_root()
    for source in sorted(root.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        rel = str(source.relative_to(root))
        raw = source.read_bytes()
        content = _fill_site_json(raw, answers) if rel == _SITE_JSON_REL else raw
        _write(repo_root / rel, content, executable=False, rel=rel, result=result)


def materialize(repo_root: Path | str, answers: Answers) -> BootstrapResult:
    """Write the foundry setup into `repo_root` deterministically and idempotently."""
    repo_root = Path(repo_root)
    result = BootstrapResult()

    files = _copy_verbatim(repo_root, answers, result)
    _copy_seeds(repo_root, answers, result)

    _write(repo_root / "AGENTS.md", _render_agents_md(answers),
           executable=False, rel="AGENTS.md", result=result)
    if "claude-code" in answers.harnesses:
        _write_symlink(repo_root / "CLAUDE.md", "AGENTS.md", "CLAUDE.md", result)

    _write(repo_root / ".foundry" / "config.toml", _render_config(answers),
           executable=False, rel=".foundry/config.toml", result=result)

    manifest = {
        "pluginVersion": __version__,
        "conventionVersion": CONVENTION_VERSION,
        "harnesses": list(answers.harnesses),
        "files": files,
    }
    result.manifest = manifest
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    _write(repo_root / ".foundry" / "manifest.json", manifest_bytes,
           executable=False, rel=".foundry/manifest.json", result=result)

    return result


def bootstrap(repo_root: Path | str, answers: Answers) -> tuple[bool, list[str]]:
    """Materialize then verify: run the gate suite against the new repo and report its
    verdict as the last output line."""
    from foundry.gate.suite import run as run_gate

    repo_root = Path(repo_root)
    result = materialize(repo_root, answers)

    lines = [f"bootstrap: wrote {len(result.written)} file(s)"]
    for rel in result.skipped:
        lines.append(f"bootstrap: skipped {rel} (exists and differs — left untouched)")
    lines.append("bootstrap: run `git config core.hooksPath .githooks` to wire the gate hook")

    ok, gate_lines = run_gate(repo_root)
    lines.extend(gate_lines)
    return ok, lines
