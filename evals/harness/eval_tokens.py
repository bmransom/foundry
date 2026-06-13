#!/usr/bin/env python3
"""Read a claude `--output-format stream-json` transcript: records, final text,
and token usage. Shared by every eval driver and grader so context cost is
measured, not estimated. Pure stdlib.

The transcript is NDJSON. The final `{"type":"result"}` record carries the
answer text (`result`), token `usage`, and `total_cost_usd`. Context cost is the
input side — what the agent loaded into the window — summed across fresh input,
cache writes, and cache reads.
"""

import json

INPUT_SIDE_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def iter_records(transcript_path):
    """Yield each parseable JSON record from a stream-json transcript."""
    with open(transcript_path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def last_result_record(transcript_path):
    """Return the final {"type":"result"} record, or None if absent."""
    result = None
    for record in iter_records(transcript_path):
        if record.get("type") == "result":
            result = record
    return result


def final_text(transcript_path):
    """The agent's final answer text (result.result), or '' if absent."""
    result = last_result_record(transcript_path)
    return (result or {}).get("result") or ""


def usage_from_transcript(transcript_path):
    """Token metrics from the result record's usage. Zeros when usage is absent
    (e.g. a pre-instrumentation transcript) so callers can label missing cost."""
    result = last_result_record(transcript_path) or {}
    usage = result.get("usage") or {}

    def field(name):
        return int(usage.get(name, 0) or 0)

    return {
        "context_tokens": sum(field(name) for name in INPUT_SIDE_FIELDS),
        "input_tokens": field("input_tokens"),
        "cache_creation_input_tokens": field("cache_creation_input_tokens"),
        "cache_read_input_tokens": field("cache_read_input_tokens"),
        "output_tokens": field("output_tokens"),
        "total_cost_usd": float(result.get("total_cost_usd", 0.0) or 0.0),
        "has_usage": bool(usage),
    }


def loaded_content_tokens(transcript_path):
    """Rough token count of the content the agent actually pulled in via tools —
    the sum of tool_result text, divided by 4. Unlike usage_from_transcript this
    excludes the fixed system-prompt overhead, so it reflects navigation cost
    rather than base context."""
    chars = 0
    for record in iter_records(transcript_path):
        if record.get("type") != "user":
            continue
        content = (record.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                continue
            inner = block.get("content")
            if isinstance(inner, str):
                chars += len(inner)
            elif isinstance(inner, list):
                for segment in inner:
                    if isinstance(segment, dict):
                        chars += len(segment.get("text", ""))
    return chars // 4
