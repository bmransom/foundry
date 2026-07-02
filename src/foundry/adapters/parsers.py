"""Harness output-format parsers: raw stdout -> normalized StageResult (design D2).

One function per output format; registered in PARSERS by the name an adapter TOML's
[headless].parser key references.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


class ParseError(Exception):
    """Raw harness output could not be parsed into a StageResult."""


@dataclass(frozen=True)
class StageResult:
    text: str
    input_tokens: int
    output_tokens: int
    exit_status: int


def parse_claude_stream_json(raw: str) -> StageResult:
    """Parse claude-code's `--output-format stream-json` JSONL stream.

    Each line is a JSON event (system/assistant/result/...); the trailing `result`
    event carries the final text and token usage. Cache fields
    (`cache_creation_input_tokens`, `cache_read_input_tokens`) count toward input
    tokens, matching the recorded conformance fixture.
    """
    result_event = None
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as e:
            raise ParseError(f"malformed stream-json at line {lineno}: {e}") from e
        if event.get("type") == "result":
            result_event = event

    if result_event is None:
        raise ParseError("no 'result' event found in stream-json output")

    text = result_event.get("result")
    if text is None:
        raise ParseError("'result' event is missing its 'result' text field")

    usage = result_event.get("usage", {})
    input_tokens = (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )
    output_tokens = usage.get("output_tokens", 0)
    exit_status = 1 if result_event.get("is_error") else 0

    return StageResult(
        text=text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        exit_status=exit_status,
    )


PARSERS = {
    "claude-stream-json": parse_claude_stream_json,
}
