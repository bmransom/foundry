"""Config loading and stage routing (design D3): config.toml + manifest.json,
resolved with precedence CLI flag > [routing.stage.<stage>] > [routing.default] >
shipped defaults. Stdlib only.
"""

from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Stage names, design D1's stage table.
STAGES = ("frame", "spec", "plan", "build", "verify", "knowledge", "review", "finish")

_MECHANICAL_STAGES = frozenset({"frame", "verify", "finish"})
_MID_TIER_STAGES = frozenset({"build", "knowledge"})
# Remaining stages (spec, plan, review) route to the top tier.

DEFAULT_HARNESS = "claude-code"
MID_TIER_MODEL = "claude-sonnet-5"
TOP_TIER_MODEL = "claude-opus-4-8"

_ROUTE_FIELDS = ("harness", "model", "effort")


class ConfigError(Exception):
    """A malformed config/manifest file, a wrong-typed key, or an unknown stage."""


@dataclass(frozen=True)
class Route:
    harness: str | None
    model: str | None
    effort: str | None = None


@dataclass(frozen=True)
class Autonomy:
    level: str = "guided"
    stop_point: str = "card"


def _shipped_default(stage: str) -> Route:
    if stage in _MECHANICAL_STAGES:
        return Route(harness=None, model=None, effort=None)
    if stage in _MID_TIER_STAGES:
        return Route(harness=DEFAULT_HARNESS, model=MID_TIER_MODEL, effort=None)
    return Route(harness=DEFAULT_HARNESS, model=TOP_TIER_MODEL, effort=None)


def _load_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: malformed TOML ({e})".replace("\n", " ")) from e


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ConfigError(f"{path}: malformed JSON ({e})".replace("\n", " ")) from e


def _table(data: dict, key: str, path: Path) -> dict:
    """Return data[key] as a dict, raising ConfigError if present but wrong-typed."""
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{path}: '{key}' must be a table")
    return value


def _str_or_none(table: dict, key: str, qualified_name: str, path: Path) -> str | None:
    value = table.get(key)
    if value is not None and not isinstance(value, str):
        raise ConfigError(f"{path}: '{qualified_name}' must be a string")
    return value


def _str_list(table: dict, key: str, qualified_name: str, path: Path) -> list:
    value = table.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ConfigError(f"{path}: '{qualified_name}' must be a list of strings")
    return value


def _routing_layer(table: dict, qualified_name: str, path: Path) -> dict:
    """Validate a [routing.default] or [routing.stage.<stage>] table: only the
    harness/model/effort keys, each a string.
    """
    layer = {}
    for key in _ROUTE_FIELDS:
        layer[key] = _str_or_none(table, key, f"{qualified_name}.{key}", path)
    return layer


@dataclass
class Config:
    pin: str | None = None
    repo_url: str | None = None
    gate_test: str | None = None
    gate_commands: list = field(default_factory=list)
    autonomy: Autonomy = field(default_factory=Autonomy)
    harnesses: frozenset = frozenset()
    _routing_default: dict = field(default_factory=dict)
    _routing_stage: dict = field(default_factory=dict)

    @classmethod
    def load(cls, repo_root: Path | str) -> "Config":
        repo_root = Path(repo_root)
        config_path = repo_root / ".foundry" / "config.toml"
        manifest_path = repo_root / ".foundry" / "manifest.json"

        data = _load_toml(config_path)
        manifest = _load_json(manifest_path)

        foundry_section = _table(data, "foundry", config_path)
        gate_section = _table(data, "gate", config_path)
        autonomy_section = _table(data, "autonomy", config_path)
        routing_section = _table(data, "routing", config_path)

        pin = _str_or_none(foundry_section, "pin", "foundry.pin", config_path)
        repo_url = _str_or_none(foundry_section, "repo_url", "foundry.repo_url", config_path)
        gate_test = _str_or_none(gate_section, "test", "gate.test", config_path)
        gate_commands = _str_list(gate_section, "commands", "gate.commands", config_path)
        autonomy = Autonomy(
            level=_str_or_none(autonomy_section, "level", "autonomy.level", config_path)
            or Autonomy().level,
            stop_point=_str_or_none(
                autonomy_section, "stop_point", "autonomy.stop_point", config_path
            )
            or Autonomy().stop_point,
        )

        routing_default_table = _table(routing_section, "default", config_path)
        routing_default = _routing_layer(routing_default_table, "routing.default", config_path)

        routing_stage_section = _table(routing_section, "stage", config_path)
        routing_stage = {}
        for stage_name, stage_table in routing_stage_section.items():
            if not isinstance(stage_table, dict):
                raise ConfigError(
                    f"{config_path}: 'routing.stage.{stage_name}' must be a table"
                )
            routing_stage[stage_name] = _routing_layer(
                stage_table, f"routing.stage.{stage_name}", config_path
            )

        harnesses = _str_list(manifest, "harnesses", "harnesses", manifest_path)

        return cls(
            pin=pin,
            repo_url=repo_url,
            gate_test=gate_test,
            gate_commands=gate_commands,
            autonomy=autonomy,
            harnesses=frozenset(harnesses),
            _routing_default=routing_default,
            _routing_stage=routing_stage,
        )

    def route_for(
        self,
        stage: str,
        harness: str | None = None,
        model: str | None = None,
        effort: str | None = None,
    ) -> Route:
        if stage not in STAGES:
            raise ConfigError(
                f"unknown stage '{stage}'; valid stages: {', '.join(STAGES)}"
            )

        shipped = _shipped_default(stage)
        resolved = {"harness": shipped.harness, "model": shipped.model, "effort": shipped.effort}
        for layer in (self._routing_default, self._routing_stage.get(stage, {})):
            for key in _ROUTE_FIELDS:
                if layer.get(key) is not None:
                    resolved[key] = layer[key]

        for key, override in zip(_ROUTE_FIELDS, (harness, model, effort)):
            if override is not None:
                resolved[key] = override

        return Route(**resolved)
