"""Tests for foundry.adapters: TOML load, argv template expansion, shell-metacharacter
rejection, availability probe, and claude-stream-json parsing against a recorded
conformance fixture (design D2).
"""

from pathlib import Path

import pytest

from foundry.adapters import (
    Adapter,
    AdapterError,
    expand_argv,
    headless,
    load,
)
from foundry.adapters.parsers import (
    ParseError,
    StageResult,
    parse_claude_stream_json,
    parse_codex_jsonl,
)
from foundry.config import Route

FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "claude-code"
CODEX_FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "codex"


# --- TOML load ---------------------------------------------------------


def test_load_claude_code_adapter():
    adapter = load("claude-code")

    assert isinstance(adapter, Adapter)
    assert adapter.name == "claude-code"
    assert adapter.instruction_file == "AGENTS.md"
    assert adapter.instruction_pointer == "CLAUDE.md"
    assert adapter.headless_command == (
        "claude", "-p", "@{prompt_file}", "--output-format", "stream-json", "--verbose",
        "--permission-mode", "acceptEdits", "--model", "{model}",
    )
    assert adapter.effort_args == ("--effort", "{effort}")
    assert adapter.parser_name == "claude-stream-json"
    assert adapter.interactive_command == ("claude", "--model", "{model}")


def test_load_unknown_adapter_raises():
    with pytest.raises(AdapterError) as excinfo:
        load("nonexistent-harness")

    assert "nonexistent-harness" in str(excinfo.value)


# --- argv template expansion --------------------------------------------


def test_expand_argv_substitutes_placeholders():
    template = ("claude", "-p", "@{prompt_file}", "--model", "{model}")

    argv = expand_argv(
        template, model="claude-sonnet-5", prompt_file="/tmp/prompt.md",
        effort=None, workspace="/tmp/ws",
    )

    assert argv == ["claude", "-p", "@/tmp/prompt.md", "--model", "claude-sonnet-5"]


def test_expand_argv_returns_a_list_never_a_string():
    template = ("claude", "--model", "{model}")

    argv = expand_argv(template, model="x", effort=None, prompt_file="p", workspace="w")

    assert isinstance(argv, list)
    assert all(isinstance(element, str) for element in argv)


def test_expand_argv_substitutes_workspace_placeholder():
    template = ("claude", "--cwd", "{workspace}")

    argv = expand_argv(template, model="x", effort=None, prompt_file="p", workspace="/repo/wt/card-1")

    assert argv == ["claude", "--cwd", "/repo/wt/card-1"]


# --- shell-metacharacter rejection ---------------------------------------


@pytest.mark.parametrize("bad_value", [
    "claude-sonnet-5; rm -rf /",
    "claude-sonnet-5 | cat /etc/passwd",
    "claude-sonnet-5 && echo pwned",
    "$(whoami)",
    "`whoami`",
    "claude-sonnet-5 > /tmp/out",
    "claude-sonnet-5 < /tmp/in",
])
def test_expand_argv_rejects_shell_metacharacters_in_values(bad_value):
    template = ("claude", "--model", "{model}")

    with pytest.raises(AdapterError):
        expand_argv(template, model=bad_value, effort=None, prompt_file="p", workspace="w")


def test_expand_argv_accepts_ordinary_values():
    template = ("claude", "--model", "{model}")

    argv = expand_argv(template, model="claude-opus-4-8", effort=None, prompt_file="p", workspace="w")

    assert argv == ["claude", "--model", "claude-opus-4-8"]


# --- effort omitted / appended -------------------------------------------


class RecordingRunner:
    def __init__(self, stdout: str):
        self.stdout = stdout
        self.calls = []
        self.stdins = []

    def __call__(self, argv, workspace, stdin=None):
        self.calls.append((list(argv), workspace))
        self.stdins.append(stdin)
        return self.stdout


def _fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_headless_omits_effort_args_when_effort_unset():
    adapter = load("claude-code")
    runner = RecordingRunner(_fixture_text("hello.stream-json.jsonl"))
    route = Route(harness="claude-code", model="claude-sonnet-5", effort=None)

    headless(adapter, "/tmp/prompt.md", route, "/tmp/ws", run=runner)

    argv, workspace = runner.calls[0]
    assert "--effort" not in argv
    assert workspace == "/tmp/ws"


def test_headless_appends_effort_args_when_effort_set():
    adapter = load("claude-code")
    runner = RecordingRunner(_fixture_text("hello.stream-json.jsonl"))
    route = Route(harness="claude-code", model="claude-sonnet-5", effort="high")

    headless(adapter, "/tmp/prompt.md", route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert argv[-2:] == ["--effort", "high"]


def test_headless_argv_contains_model_and_prompt_file():
    adapter = load("claude-code")
    runner = RecordingRunner(_fixture_text("hello.stream-json.jsonl"))
    route = Route(harness="claude-code", model="claude-sonnet-5", effort=None)

    headless(adapter, "/tmp/prompt.md", route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert "claude-sonnet-5" in argv
    assert "@/tmp/prompt.md" in argv


def test_headless_returns_parsed_stage_result():
    adapter = load("claude-code")
    runner = RecordingRunner(_fixture_text("hello.stream-json.jsonl"))
    route = Route(harness="claude-code", model="claude-sonnet-5", effort=None)

    result = headless(adapter, "/tmp/prompt.md", route, "/tmp/ws", run=runner)

    assert isinstance(result, StageResult)
    assert result.text == "ok"
    assert result.exit_status == 0


# --- availability probe --------------------------------------------------


def test_available_true_when_command_on_path(monkeypatch):
    adapter = load("claude-code")
    monkeypatch.setattr("shutil.which", lambda cmd: "/usr/local/bin/claude")

    assert adapter.available() is True


def test_available_false_when_command_missing(monkeypatch):
    adapter = load("claude-code")
    monkeypatch.setattr("shutil.which", lambda cmd: None)

    assert adapter.available() is False


# --- parser vs the recorded conformance fixture ---------------------------


def test_parse_claude_stream_json_against_recorded_fixture():
    raw = _fixture_text("hello.stream-json.jsonl")

    result = parse_claude_stream_json(raw)

    assert result == StageResult(
        text="ok",
        input_tokens=4229 + 0 + 20327,  # input + cache_creation + cache_read
        output_tokens=4,
        exit_status=0,
    )


def test_parse_claude_stream_json_on_malformed_input_raises_clear_error():
    raw = _fixture_text("malformed.stream-json.jsonl")

    with pytest.raises(ParseError) as excinfo:
        parse_claude_stream_json(raw)

    assert "\n" not in str(excinfo.value)


def test_parse_claude_stream_json_missing_result_event_raises():
    raw = _fixture_text("no-result.stream-json.jsonl")

    with pytest.raises(ParseError) as excinfo:
        parse_claude_stream_json(raw)

    assert "result" in str(excinfo.value)


def test_parse_claude_stream_json_on_empty_input_raises():
    with pytest.raises(ParseError):
        parse_claude_stream_json("")


def test_parse_claude_stream_json_is_error_maps_to_nonzero_exit_status():
    # Synthetic: shaped like the recorded fixture's result event but with is_error
    # true, a branch the (successful) recorded conformance fixture never exercises.
    raw = (
        '{"type":"result","subtype":"error","is_error":true,"result":"boom",'
        '"usage":{"input_tokens":10,"output_tokens":2}}'
    )

    result = parse_claude_stream_json(raw)

    assert result.exit_status == 1
    assert result.text == "boom"


# --- codex: TOML load -----------------------------------------------------


def test_load_codex_adapter():
    adapter = load("codex")

    assert isinstance(adapter, Adapter)
    assert adapter.name == "codex"
    assert adapter.instruction_file == "AGENTS.md"
    assert adapter.headless_command == (
        "codex", "exec", "--json", "--sandbox", "workspace-write",
        "-m", "{model}", "-",
    )
    assert adapter.effort_args == ("-c", "model_reasoning_effort={effort}")
    assert adapter.parser_name == "codex-jsonl"
    assert adapter.interactive_command == ("codex", "-m", "{model}")


def test_load_codex_adapter_tolerates_missing_pointer():
    # codex reads AGENTS.md natively: no CLAUDE.md-style symlink pointer needed.
    adapter = load("codex")

    assert adapter.instruction_pointer is None


# --- codex: effort omitted / appended -------------------------------------


def _codex_fixture_text(name: str) -> str:
    return (CODEX_FIXTURES / name).read_text()


def test_codex_headless_omits_effort_args_when_effort_unset(tmp_path):
    adapter = load("codex")
    runner = RecordingRunner(_codex_fixture_text("hello.jsonl"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hi", encoding="utf-8")
    route = Route(harness="codex", model="gpt-5.5", effort=None)

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, workspace = runner.calls[0]
    assert "-c" not in argv
    assert "model_reasoning_effort=high" not in argv
    assert workspace == "/tmp/ws"


def test_codex_headless_appends_effort_args_when_effort_set(tmp_path):
    adapter = load("codex")
    runner = RecordingRunner(_codex_fixture_text("hello.jsonl"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hi", encoding="utf-8")
    route = Route(harness="codex", model="gpt-5.5", effort="high")

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert argv[-2:] == ["-c", "model_reasoning_effort=high"]


def test_codex_headless_returns_parsed_stage_result(tmp_path):
    adapter = load("codex")
    runner = RecordingRunner(_codex_fixture_text("hello.jsonl"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hi", encoding="utf-8")
    route = Route(harness="codex", model="gpt-5.5", effort=None)

    result = headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    assert isinstance(result, StageResult)
    assert result.text == "ok"
    assert result.exit_status == 0


# --- codex: parser vs the recorded conformance fixtures --------------------


def test_parse_codex_jsonl_against_recorded_hello_fixture():
    raw = _codex_fixture_text("hello.jsonl")

    result = parse_codex_jsonl(raw)

    assert result == StageResult(
        text="ok",
        input_tokens=13948,  # already totals cached_input_tokens (OpenAI usage semantics)
        output_tokens=20,    # already totals reasoning_output_tokens
        exit_status=0,
    )


def test_parse_codex_jsonl_against_recorded_error_fixture():
    # Real recorded transcript: `codex exec --json -m totally-bogus-model-xyz ...`
    raw = _codex_fixture_text("error.jsonl")

    result = parse_codex_jsonl(raw)

    assert result.exit_status == 1
    assert "not supported" in result.text
    assert result.input_tokens == 0
    assert result.output_tokens == 0


def test_parse_codex_jsonl_on_malformed_input_raises_clear_error():
    raw = _codex_fixture_text("malformed.jsonl")

    with pytest.raises(ParseError) as excinfo:
        parse_codex_jsonl(raw)

    assert "\n" not in str(excinfo.value)


def test_parse_codex_jsonl_missing_agent_message_raises():
    raw = _codex_fixture_text("no-result.jsonl")

    with pytest.raises(ParseError) as excinfo:
        parse_codex_jsonl(raw)

    assert "agent_message" in str(excinfo.value)


def test_parse_codex_jsonl_on_empty_input_raises():
    with pytest.raises(ParseError):
        parse_codex_jsonl("")


# --- prompt delivery: codex has no @file expansion, so a bare "-" in the
# expanded argv means "pipe prompt_file's content over stdin" (T9's flagged
# gap); claude keeps @{prompt_file} and gets no stdin. -------------------------


def test_headless_pipes_prompt_file_content_via_stdin_when_argv_has_bare_dash(tmp_path):
    adapter = load("codex")
    runner = RecordingRunner(_codex_fixture_text("hello.jsonl"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("do the thing", encoding="utf-8")
    route = Route(harness="codex", model="gpt-5.5", effort=None)

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert argv[-1] == "-"
    assert runner.stdins[0] == "do the thing"


def test_headless_claude_path_gets_no_stdin(tmp_path):
    adapter = load("claude-code")
    runner = RecordingRunner(_fixture_text("hello.stream-json.jsonl"))
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("do the thing", encoding="utf-8")
    route = Route(harness="claude-code", model="claude-sonnet-5", effort=None)

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert f"@{prompt_file}" in argv
    assert runner.stdins[0] is None


# --- AC-3.3: effort omitted where unsupported, per-harness shape when set ----


@pytest.mark.parametrize("adapter_name,model,fixture_text", [
    ("claude-code", "claude-sonnet-5", "hello.stream-json.jsonl"),
    ("codex", "gpt-5.5", "hello.jsonl"),
])
def test_effort_omitted_for_both_adapters_when_unset(adapter_name, model, fixture_text, tmp_path):
    adapter = load(adapter_name)
    fixture = _fixture_text(fixture_text) if adapter_name == "claude-code" else _codex_fixture_text(fixture_text)
    runner = RecordingRunner(fixture)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hi", encoding="utf-8")
    route = Route(harness=adapter_name, model=model, effort=None)

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert "--effort" not in argv
    assert not any("model_reasoning_effort" in a for a in argv)


@pytest.mark.parametrize("adapter_name,model,fixture_text,expected_tail", [
    ("claude-code", "claude-sonnet-5", "hello.stream-json.jsonl", ["--effort", "high"]),
    ("codex", "gpt-5.5", "hello.jsonl", ["-c", "model_reasoning_effort=high"]),
])
def test_effort_shape_is_per_harness_when_set(adapter_name, model, fixture_text, expected_tail, tmp_path):
    adapter = load(adapter_name)
    fixture = _fixture_text(fixture_text) if adapter_name == "claude-code" else _codex_fixture_text(fixture_text)
    runner = RecordingRunner(fixture)
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("hi", encoding="utf-8")
    route = Route(harness=adapter_name, model=model, effort="high")

    headless(adapter, str(prompt_file), route, "/tmp/ws", run=runner)

    argv, _ = runner.calls[0]
    assert argv[-len(expected_tail):] == expected_tail
