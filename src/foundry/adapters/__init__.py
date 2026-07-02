"""Harness adapter loader (design D2): TOML load, argv template expansion, availability
probe, and the headless runner that hands captured stdout to a named parser.

Command templates are argv lists with {model}, {effort}, {prompt_file}, {workspace}
placeholders — never joined into a shell string, and executed via subprocess with no
shell (no injection surface). Substituted values are additionally rejected if they
contain shell metacharacters, as defense in depth.
"""

from __future__ import annotations

import shutil
import subprocess
import tomllib
from dataclasses import dataclass
from importlib import resources
from typing import Callable

from foundry.adapters.parsers import PARSERS, StageResult
from foundry.config import Route

_SHELL_METACHARACTERS = frozenset(";|&$`<>")

_PLACEHOLDER_KEYS = ("model", "effort", "prompt_file", "workspace")


class AdapterError(Exception):
    """An adapter TOML failed to load, or an argv template value is unsafe."""


@dataclass(frozen=True)
class Adapter:
    name: str
    instruction_file: str
    instruction_pointer: str
    headless_command: tuple
    effort_args: tuple
    parser_name: str
    interactive_command: tuple

    def available(self) -> bool:
        """Probe: is the adapter's headless command on PATH."""
        binary = self.headless_command[0]
        return shutil.which(binary) is not None


def _table(data: dict, key: str, adapter_name: str) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        raise AdapterError(f"{adapter_name}.toml: missing or malformed '{key}' table")
    return value


def _str(table: dict, key: str, qualified_name: str) -> str:
    value = table.get(key)
    if not isinstance(value, str):
        raise AdapterError(f"{qualified_name}.{key}: must be a string")
    return value


def _str_list(table: dict, key: str, qualified_name: str) -> tuple:
    value = table.get(key)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise AdapterError(f"{qualified_name}.{key}: must be a list of strings")
    return tuple(value)


def load(name: str) -> Adapter:
    """Load an adapter TOML shipped under src/foundry/adapters/<name>.toml."""
    resource = resources.files("foundry.adapters").joinpath(f"{name.replace('-', '_')}.toml")
    if not resource.is_file():
        raise AdapterError(f"no adapter named '{name}' (looked for {resource})")

    with resource.open("rb") as f:
        data = tomllib.load(f)

    adapter_name = _str(data, "name", name)
    instruction = _table(data, "instruction", adapter_name)
    headless = _table(data, "headless", adapter_name)
    interactive = _table(data, "interactive", adapter_name)

    return Adapter(
        name=adapter_name,
        instruction_file=_str(instruction, "file", f"{adapter_name}.instruction"),
        instruction_pointer=_str(instruction, "pointer", f"{adapter_name}.instruction"),
        headless_command=_str_list(headless, "command", f"{adapter_name}.headless"),
        effort_args=_str_list(headless, "effort_args", f"{adapter_name}.headless")
        if "effort_args" in headless
        else (),
        parser_name=_str(headless, "parser", f"{adapter_name}.headless"),
        interactive_command=_str_list(interactive, "command", f"{adapter_name}.interactive"),
    )


def _reject_shell_metacharacters(name: str, value: str) -> None:
    found = _SHELL_METACHARACTERS & set(value)
    if found:
        raise AdapterError(
            f"argv value for {{{name}}}={value!r} contains shell metacharacters: "
            f"{''.join(sorted(found))} (argv templates take literal values, never shell text)"
        )


def expand_argv(template, **values) -> list:
    """Expand an argv template tuple, substituting {model}/{effort}/{prompt_file}/
    {workspace} placeholders. Returns a plain argv list — never a shell string.
    Raises AdapterError if any substituted value contains a shell metacharacter.
    """
    substitutions = {}
    for key in _PLACEHOLDER_KEYS:
        value = values.get(key)
        if value is None:
            continue
        _reject_shell_metacharacters(key, value)
        substitutions[key] = value

    expanded = []
    for element in template:
        try:
            expanded.append(element.format(**substitutions))
        except KeyError as e:
            raise AdapterError(f"argv template element {element!r} needs {e}, not supplied") from e
    return expanded


def available(adapter: Adapter) -> bool:
    return adapter.available()


def _run_subprocess(argv: list, workspace: str) -> str:
    completed = subprocess.run(
        argv, cwd=workspace, capture_output=True, text=True, check=False,
    )
    return completed.stdout


def headless(
    adapter: Adapter,
    prompt_file: str,
    route: Route,
    workspace: str,
    *,
    run: Callable[[list, str], str] | None = None,
) -> StageResult:
    """Run the adapter's headless command for one stage, capture stdout, and parse it.

    `run` is injectable (argv, workspace) -> str, so tests can supply a fake
    subprocess runner instead of spawning the real harness CLI.
    """
    run = run or _run_subprocess

    argv = expand_argv(
        adapter.headless_command,
        model=route.model,
        effort=route.effort,
        prompt_file=prompt_file,
        workspace=workspace,
    )
    if route.effort:
        argv += expand_argv(
            adapter.effort_args,
            model=route.model,
            effort=route.effort,
            prompt_file=prompt_file,
            workspace=workspace,
        )

    raw_stdout = run(argv, workspace)

    if adapter.parser_name not in PARSERS:
        raise AdapterError(f"no parser registered for '{adapter.parser_name}'")
    parser = PARSERS[adapter.parser_name]
    return parser(raw_stdout)
