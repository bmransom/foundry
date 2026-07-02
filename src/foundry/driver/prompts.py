"""Stage-prompt compilation (design D8, US-10).

The driver hands a judgment stage to a harness as a single prompt: the stage's
rubric(s) plus the card context. This module assembles that prompt deterministically —
no timestamps, no environment leakage — so a compiled prompt is a pure function of the
stage, the rubrics on disk, and the card.

Two sources feed a stage's `rubrics` tuple (from `stages.py`):

- a **stage rubric** shipped in the package (`src/foundry/rubrics/<name>.md`), loaded
  via importlib.resources; or
- an **advisory skill** (`plugins/foundry/skills/<name>/SKILL.md`), composed by
  reference from the repo tree — its body, frontmatter stripped.

A stage rubric wins when a name resolves both ways (the extracted judgment supersedes the
interactive skill).

A rubric never carries an orchestration verb — worktree, commit, board, push, branch are
driver vocabulary, not stage judgment (D8). `validate_rubric` rejects one; every load
runs it, so a seeded orchestration verb fails compilation rather than reaching a harness.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from foundry.driver.stages import Stage

RUBRICS_PACKAGE = "foundry.rubrics"

# Driver vocabulary a stage rubric may never carry (design D8).
ORCHESTRATION_VERBS = ("worktree", "commit", "board", "push", "branch")
_VERB_RE = {
    verb: re.compile(rf"\b{verb}\b", re.IGNORECASE) for verb in ORCHESTRATION_VERBS
}

_SEPARATOR = "\n\n---\n\n"


class RubricError(Exception):
    """A rubric is missing, or carries an orchestration verb (driver vocabulary)."""


@dataclass(frozen=True)
class CardContext:
    """The card facts a stage prompt closes over: which card, its spec files, its
    worktree path, and the run's autonomy level. Plain data — no timestamps."""

    card_id: str
    spec_paths: tuple
    worktree: str
    autonomy: str


def validate_rubric(name: str, text: str) -> None:
    """Raise RubricError if `text` carries an orchestration verb.

    Orchestration is the driver's job; a stage rubric holds judgment only (D8). Matching
    is word-boundary and case-insensitive over the whole rubric.
    """
    for verb, pattern in _VERB_RE.items():
        if pattern.search(text):
            raise RubricError(
                f"rubric '{name}' carries the orchestration verb '{verb}' — "
                f"worktree/board/commit/push/branch are driver vocabulary, not stage "
                f"judgment (design D8)"
            )


def load_rubric(name: str) -> str:
    """Load and validate a stage rubric shipped at src/foundry/rubrics/<name>.md."""
    resource = resources.files(RUBRICS_PACKAGE).joinpath(f"{name}.md")
    if not resource.is_file():
        raise RubricError(f"no rubric named '{name}' (looked for {resource})")
    text = resource.read_text(encoding="utf-8").rstrip("\n")
    validate_rubric(name, text)
    return text


def _repo_root() -> Path:
    # src/foundry/driver/prompts.py -> repo root is three parents up from the package.
    return Path(__file__).resolve().parents[3]


def _strip_frontmatter(text: str) -> str:
    """Return a SKILL.md body with a leading `---`-delimited YAML block removed."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip("\n")
    return text


def _advisory_skill_body(name: str, skills_root: Path) -> str | None:
    """Compose an advisory skill's body by reference, or None if there is no such skill."""
    skill = skills_root / name / "SKILL.md"
    if not skill.is_file():
        return None
    return _strip_frontmatter(skill.read_text(encoding="utf-8")).rstrip("\n")


def _resolve_section(name: str, skills_root: Path) -> str:
    """A rubric name -> its prompt section: a package rubric, else an advisory skill."""
    try:
        return load_rubric(name)
    except RubricError as rubric_missing:
        body = _advisory_skill_body(name, skills_root)
        if body is None:
            raise RubricError(
                f"rubric name '{name}' resolves to neither a package rubric nor an "
                f"advisory skill under {skills_root}"
            ) from rubric_missing
        return body


def _card_context_block(card: CardContext) -> str:
    specs = "\n".join(f"  - {p}" for p in card.spec_paths)
    return (
        "## Card context\n\n"
        f"- Card: {card.card_id}\n"
        f"- Autonomy: {card.autonomy}\n"
        f"- Worktree: {card.worktree}\n"
        "- Spec files:\n"
        f"{specs}"
    )


def compile_stage_prompt(
    stage: Stage,
    card_context: CardContext,
    *,
    skills_root: Path | None = None,
) -> str:
    """Compile a judgment stage's prompt: its rubric(s) plus the card context.

    Deterministic — a pure function of the stage, the rubrics/skills on disk, and the
    card. `skills_root` overrides the advisory-skill lookup for tests; it defaults to the
    repo's `plugins/foundry/skills/` tree (design D8 "composed by reference").
    """
    if skills_root is None:
        skills_root = _repo_root() / "plugins" / "foundry" / "skills"
    sections = [_resolve_section(name, skills_root) for name in stage.rubrics]
    sections.append(_card_context_block(card_context))
    return _SEPARATOR.join(sections) + "\n"
