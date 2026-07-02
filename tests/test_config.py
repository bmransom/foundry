"""Tests for foundry.config: routing precedence, shipped defaults, error handling."""

from pathlib import Path

import pytest

from foundry.config import Config, ConfigError, STAGES


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# --- missing file -> shipped defaults --------------------------------------


def test_missing_config_and_manifest_uses_shipped_defaults(tmp_path):
    config = Config.load(tmp_path)

    assert config.pin is None
    assert config.repo_url is None
    assert config.gate_test is None
    assert config.gate_commands == []
    assert config.autonomy.level == "guided"
    assert config.autonomy.stop_point == "card"
    assert config.harnesses == frozenset()


def test_shipped_defaults_route_mechanical_stages_to_no_model(tmp_path):
    config = Config.load(tmp_path)

    for stage in ("frame", "verify", "finish"):
        route = config.route_for(stage)
        assert route.harness is None
        assert route.model is None
        assert route.effort is None


def test_shipped_defaults_route_mid_tier_stages(tmp_path):
    config = Config.load(tmp_path)

    for stage in ("build", "knowledge"):
        route = config.route_for(stage)
        assert route.harness == "claude-code"
        assert route.model == "claude-sonnet-5"
        assert route.effort is None


def test_shipped_defaults_route_top_tier_stages(tmp_path):
    config = Config.load(tmp_path)

    for stage in ("spec", "plan", "review"):
        route = config.route_for(stage)
        assert route.harness == "claude-code"
        assert route.model == "claude-opus-4-8"
        assert route.effort is None


# --- precedence: shipped < [routing.default] < [routing.stage.X] < CLI flag


def test_routing_default_overrides_shipped(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [routing.default]
        harness = "codex"
        model = "gpt-5.5"
        """,
    )
    config = Config.load(tmp_path)

    route = config.route_for("spec")
    assert route.harness == "codex"
    assert route.model == "gpt-5.5"


def test_routing_stage_overrides_routing_default(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [routing.default]
        harness = "claude-code"
        model = "claude-opus-4-8"

        [routing.stage.build]
        model = "claude-sonnet-5"
        """,
    )
    config = Config.load(tmp_path)

    route = config.route_for("build")
    assert route.harness == "claude-code"  # inherited from [routing.default]
    assert route.model == "claude-sonnet-5"  # overridden at stage layer

    # A different stage is unaffected by the stage-specific override.
    other = config.route_for("review")
    assert other.model == "claude-opus-4-8"


def test_cli_flag_overrides_everything(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [routing.default]
        harness = "claude-code"
        model = "claude-opus-4-8"

        [routing.stage.build]
        model = "claude-sonnet-5"
        """,
    )
    config = Config.load(tmp_path)

    route = config.route_for("build", harness="codex", model="gpt-5.5", effort="high")
    assert route.harness == "codex"
    assert route.model == "gpt-5.5"
    assert route.effort == "high"


def test_effort_omitted_when_unset(tmp_path):
    config = Config.load(tmp_path)

    route = config.route_for("review")
    assert route.effort is None


def test_effort_set_via_stage_routing(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [routing.stage.review]
        effort = "high"
        """,
    )
    config = Config.load(tmp_path)

    route = config.route_for("review")
    assert route.effort == "high"
    # Unaffected fields still fall through to shipped defaults.
    assert route.harness == "claude-code"
    assert route.model == "claude-opus-4-8"


# --- autonomy / pin / gate fields -------------------------------------------


def test_autonomy_pin_and_gate_fields_load_from_config(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [foundry]
        pin = "v2.0.0"
        repo_url = "https://github.com/bmransom/foundry"

        [gate]
        test = "uv run pytest -q"
        commands = ["scripts/check-heavy.sh"]

        [autonomy]
        level = "autonomous"
        stop_point = "epic"
        """,
    )
    config = Config.load(tmp_path)

    assert config.pin == "v2.0.0"
    assert config.repo_url == "https://github.com/bmransom/foundry"
    assert config.gate_test == "uv run pytest -q"
    assert config.gate_commands == ["scripts/check-heavy.sh"]
    assert config.autonomy.level == "autonomous"
    assert config.autonomy.stop_point == "epic"


def test_manifest_harnesses_set_loads(tmp_path):
    write(
        tmp_path / ".foundry" / "manifest.json",
        """{"harnesses": ["claude-code", "codex"]}""",
    )
    config = Config.load(tmp_path)

    assert config.harnesses == frozenset({"claude-code", "codex"})


# --- error handling -----------------------------------------------------


def test_malformed_toml_raises_config_error(tmp_path):
    write(tmp_path / ".foundry" / "config.toml", "this is not [ valid toml")

    with pytest.raises(ConfigError) as excinfo:
        Config.load(tmp_path)

    message = str(excinfo.value)
    assert "config.toml" in message
    assert "\n" not in message


def test_malformed_manifest_json_raises_config_error(tmp_path):
    write(tmp_path / ".foundry" / "manifest.json", "{not valid json")

    with pytest.raises(ConfigError) as excinfo:
        Config.load(tmp_path)

    message = str(excinfo.value)
    assert "manifest.json" in message
    assert "\n" not in message


def test_wrong_typed_key_raises_config_error(tmp_path):
    write(
        tmp_path / ".foundry" / "config.toml",
        """
        [gate]
        commands = "scripts/check-heavy.sh"
        """,
    )

    with pytest.raises(ConfigError) as excinfo:
        Config.load(tmp_path)

    message = str(excinfo.value)
    assert "gate.commands" in message
    assert "\n" not in message


def test_wrong_typed_manifest_key_raises_config_error(tmp_path):
    write(
        tmp_path / ".foundry" / "manifest.json",
        """{"harnesses": "claude-code"}""",
    )

    with pytest.raises(ConfigError) as excinfo:
        Config.load(tmp_path)

    message = str(excinfo.value)
    assert "harnesses" in message
    assert "manifest.json" in message


def test_unknown_stage_raises_config_error_listing_valid_stages(tmp_path):
    config = Config.load(tmp_path)

    with pytest.raises(ConfigError) as excinfo:
        config.route_for("bogus-stage")

    message = str(excinfo.value)
    assert "bogus-stage" in message
    for stage in STAGES:
        assert stage in message
