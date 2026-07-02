"""T6 — stage-prompt compilation (design D8, US-10).

The driver compiles a judgment stage's prompt from the stage's rubric(s) and card
context. A rubric never carries an orchestration verb (worktree/commit/board/push/branch
— driver vocabulary); prompts.validate_rubric enforces that. Golden fixtures pin the
compiled spec and review prompts so a rubric or assembly change is a visible diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from foundry.driver import prompts
from foundry.driver.stages import STAGES, Stage

FIXTURES = Path(__file__).parent / "fixtures" / "prompts"
RUBRICS_DIR = Path(__file__).resolve().parents[1] / "src" / "foundry" / "rubrics"
REPO_ROOT = Path(__file__).resolve().parents[1]

# A sample card, shared by the golden fixtures.
SAMPLE_CARD = prompts.CardContext(
    card_id="v2-sample",
    spec_paths=("roadmap/specs/foundry-v2/requirements.md",
                "roadmap/specs/foundry-v2/design.md",
                "roadmap/specs/foundry-v2/tasks.md"),
    worktree="wt/v2-sample",
    autonomy="guided",
)


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# --- rubric loading + validation -------------------------------------------

def test_load_rubric_returns_body():
    text = prompts.load_rubric("spec")
    assert "Spec stage rubric" in text


def test_load_rubric_unknown_raises():
    with pytest.raises(prompts.RubricError):
        prompts.load_rubric("does-not-exist")


@pytest.mark.parametrize("verb", ["worktree", "commit", "board", "push", "branch"])
def test_validate_rubric_rejects_orchestration_verb(verb):
    seeded = f"# Rogue rubric\n\nFirst {verb} the change, then judge it.\n"
    with pytest.raises(prompts.RubricError) as exc:
        prompts.validate_rubric("rogue", seeded)
    assert verb in str(exc.value)


def test_validate_rubric_accepts_clean_text():
    prompts.validate_rubric("clean", "# Fine\n\nJudge the diff against its spec.\n")


@pytest.mark.parametrize("name", ["spec", "plan", "build", "knowledge", "review"])
def test_real_rubrics_are_orchestration_free(name):
    # The validator run over every shipped rubric — none may carry a driver verb.
    text = (RUBRICS_DIR / f"{name}.md").read_text()
    prompts.validate_rubric(name, text)  # raises on violation


# --- spec rubric obligations (AC-10.4, AC-10.5) ----------------------------

def test_spec_rubric_requires_surface_invariants_and_open_questions():
    text = prompts.load_rubric("spec")
    assert "Public surface" in text
    assert "Invariants" in text
    assert "open_questions" in text


# --- compilation ------------------------------------------------------------

def test_compile_is_deterministic():
    a = prompts.compile_stage_prompt(STAGES["spec"], SAMPLE_CARD)
    b = prompts.compile_stage_prompt(STAGES["spec"], SAMPLE_CARD)
    assert a == b


def test_compile_embeds_card_context():
    out = prompts.compile_stage_prompt(STAGES["review"], SAMPLE_CARD)
    assert "v2-sample" in out
    assert "wt/v2-sample" in out
    assert "guided" in out
    assert "roadmap/specs/foundry-v2/design.md" in out


def test_compile_spec_matches_golden():
    out = prompts.compile_stage_prompt(STAGES["spec"], SAMPLE_CARD)
    assert out == _read_fixture("spec.txt")


def test_compile_review_matches_golden():
    out = prompts.compile_stage_prompt(STAGES["review"], SAMPLE_CARD)
    assert out == _read_fixture("review.txt")


def test_compile_appends_advisory_skill_body():
    # A stage whose rubric list names an advisory skill (not a package rubric)
    # composes that skill's body by reference from the repo tree.
    synthetic = Stage("synthetic", "judgment", gate_name="x",
                      rubrics=("naming-standards",))
    out = prompts.compile_stage_prompt(synthetic, SAMPLE_CARD)
    skill_body = (REPO_ROOT / "plugins" / "foundry" / "skills"
                  / "naming-standards" / "SKILL.md").read_text()
    # The composed body carries the skill's content, frontmatter stripped.
    assert "naming-standards" in skill_body  # frontmatter present in source
    assert "---\nname: naming-standards" not in out  # stripped in the prompt
    # A distinctive line from the skill body appears in the compiled prompt.
    marker = skill_body.split("---", 2)[-1].strip().splitlines()[0].lstrip("# ").strip()
    assert marker in out


# --- seed marker parity -----------------------------------------------------

def test_seed_markers_match_between_readme_copies():
    seed = (REPO_ROOT / "plugins" / "foundry" / "templates" / "seeds"
            / "roadmap" / "specs" / "README.md").read_text()
    repo = (REPO_ROOT / "roadmap" / "specs" / "README.md").read_text()
    marker = "<!-- foundry-seed: specs-readme v4 -->"
    assert marker in seed
    assert marker in repo


def test_seed_readmes_require_surface_and_invariants():
    for path in (
        REPO_ROOT / "plugins" / "foundry" / "templates" / "seeds"
        / "roadmap" / "specs" / "README.md",
        REPO_ROOT / "roadmap" / "specs" / "README.md",
    ):
        text = path.read_text()
        assert "Public surface" in text
        assert "Invariants" in text
