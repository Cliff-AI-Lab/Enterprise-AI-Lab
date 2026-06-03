from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from rd_llm_adapter.events import (
    ReasoningDelta,
    TextDelta,
    ToolCallArgsDelta,
    ToolCallEnd,
    ToolCallNameDelta,
    TurnDone,
    UsageUpdate,
)
from rd_llm_adapter.messages import InvalidToolCall, ToolUseBlock
from rd_llm_adapter.openai_compat import (
    OpenAICompatAdapter,
    OpenAICompatParserSession,
    legacy_response_from_turn_done,
    standard_event_to_legacy_delta,
    terminal_events_from_turn_done,
)


def _chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    tool_calls: list[Any] | None = None,
    finish_reason: str | None = None,
    usage: Any | None = None,
    choices: list[Any] | None = None,
) -> Any:
    if choices is None:
        delta = SimpleNamespace(
            content=content,
            model_extra=(
                {"reasoning_content": reasoning} if reasoning is not None else {}
            ),
            tool_calls=tool_calls,
        )
        choices = [SimpleNamespace(delta=delta, finish_reason=finish_reason)]
    return SimpleNamespace(choices=choices, usage=usage)


def _tool_delta(
    *,
    index: int = 0,
    call_id: str | None = None,
    name: str | None = None,
    arguments: str | None = None,
) -> Any:
    return SimpleNamespace(
        index=index,
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_build_request_matches_legacy_openai_message_shape() -> None:
    adapter = OpenAICompatAdapter()

    request = adapter.build_request(
        model="deepseek-reasoner",
        system_prompt="sys",
        messages=[
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "hello"}],
                "reasoning_content": "think",
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "I will call"},
                    {
                        "type": "tool_use",
                        "id": "call_1",
                        "name": "search",
                        "input": {"query": "x"},
                    },
                ],
                "reasoning_content": "tool-think",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_1",
                        "content": {"ok": True},
                    }
                ],
            },
        ],
        tools=[
            {
                "name": "search",
                "description": "Search",
                "input_schema": {"type": "object"},
            }
        ],
        max_tokens=1024,
        supports_function_calling=True,
        supports_stream_usage=True,
    )

    assert request["model"] == "deepseek-reasoner"
    assert request["stream"] is True
    assert request["stream_options"] == {"include_usage": True}
    assert request["messages"][0] == {"role": "system", "content": "sys"}
    assert request["messages"][1] == {
        "role": "assistant",
        "content": "hello",
        "reasoning_content": "think",
    }
    assert (
        request["messages"][2]["tool_calls"][0]["function"]["arguments"]
        == '{"query": "x"}'
    )
    assert request["messages"][2]["reasoning_content"] == "tool-think"
    assert request["messages"][3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"ok": true}',
    }
    assert request["tools"][0]["function"]["name"] == "search"


def test_build_request_preserves_explicit_empty_reasoning_content() -> None:
    adapter = OpenAICompatAdapter()

    request = adapter.build_request(
        model="deepseek-reasoner",
        system_prompt="",
        messages=[
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "call_empty_reasoning",
                        "name": "noop",
                        "input": {},
                    },
                ],
                "reasoning_content": "",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "call_empty_reasoning",
                        "content": "ok",
                    }
                ],
            },
        ],
        tools=[],
        max_tokens=16,
        supports_function_calling=True,
        supports_stream_usage=True,
    )

    assert request["messages"][0]["role"] == "assistant"
    assert request["messages"][0]["reasoning_content"] == ""


def test_parser_preserves_reasoning_text_usage_and_terminal_response() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(session.feed(_chunk(reasoning="plan ", content="hel")))
    events.extend(
        session.feed(_chunk(reasoning="done", content="lo", finish_reason="stop"))
    )
    events.extend(
        session.feed(
            _chunk(
                usage=SimpleNamespace(
                    prompt_tokens=10, completion_tokens=20, total_tokens=30
                ),
                choices=[],
            )
        )
    )
    events.extend(session.finalize())

    assert any(
        isinstance(event, ReasoningDelta) and event.text == "plan " for event in events
    )
    assert any(isinstance(event, TextDelta) and event.text == "hel" for event in events)
    assert any(
        isinstance(event, UsageUpdate) and event.total_tokens == 30 for event in events
    )

    turn_done = next(event for event in events if isinstance(event, TurnDone))
    response = legacy_response_from_turn_done(
        turn_done, latency_ms=12, first_chunk_latency_ms=3
    )
    assert response == {
        "content": [{"type": "text", "text": "hello"}],
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
        "stop_reason": "stop",
        "latency_ms": 12,
        "first_chunk_latency_ms": 3,
        "reasoning_text": "plan done",
        "text_content": "hello",
    }


def test_parser_reads_direct_reasoning_content_from_dict_chunks() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            {
                "choices": [
                    {
                        "delta": {
                            "content": None,
                            "reasoning_content": "plan ",
                            "tool_calls": None,
                        },
                        "finish_reason": None,
                    }
                ],
                "usage": None,
            }
        )
    )
    events.extend(
        session.feed(
            {
                "choices": [
                    {
                        "delta": {
                            "content": None,
                            "reasoning_content": "done",
                            "tool_calls": None,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": None,
            }
        )
    )
    events.extend(session.finalize())

    assert [
        event.text for event in events if isinstance(event, ReasoningDelta)
    ] == ["plan ", "done"]
    turn_done = next(event for event in events if isinstance(event, TurnDone))
    response = legacy_response_from_turn_done(
        turn_done, latency_ms=12, first_chunk_latency_ms=3
    )
    assert response["reasoning_text"] == "plan done"


def test_parser_reads_openrouter_reasoning_field_from_dict_chunks() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            {
                "choices": [
                    {
                        "delta": {
                            "content": None,
                            "reasoning": "hidden plan",
                            "tool_calls": None,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": None,
            }
        )
    )
    events.extend(session.finalize())

    assert [
        event.text for event in events if isinstance(event, ReasoningDelta)
    ] == ["hidden plan"]
    turn_done = next(event for event in events if isinstance(event, TurnDone))
    assert turn_done.reasoning_blocks[0].text == "hidden plan"


def test_parser_reads_reasoning_details_when_direct_reasoning_absent() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            {
                "choices": [
                    {
                        "delta": {
                            "content": None,
                            "reasoning_details": [
                                {"type": "reasoning.text", "text": "step 1 "},
                                {"type": "reasoning.text", "text": "step 2"},
                            ],
                            "tool_calls": None,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": None,
            }
        )
    )
    events.extend(session.finalize())

    assert [
        event.text for event in events if isinstance(event, ReasoningDelta)
    ] == ["step 1 step 2"]


def test_parser_preserves_usage_detail_tokens() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            _chunk(
                usage={
                    "prompt_tokens": 0,
                    "completion_tokens": 5,
                    "total_tokens": 5,
                    "prompt_tokens_details": {"cached_tokens": 123},
                    "completion_tokens_details": {"reasoning_tokens": 4},
                },
                choices=[],
            )
        )
    )
    events.extend(session.finalize())

    usage = next(event for event in events if isinstance(event, UsageUpdate))
    assert usage.to_dict() == {
        "input_tokens": 0,
        "output_tokens": 5,
        "total_tokens": 5,
        "cache_read_input_tokens": 123,
        "cached_input_tokens": 123,
        "reasoning_tokens": 4,
    }
    turn_done = next(event for event in events if isinstance(event, TurnDone))
    response = legacy_response_from_turn_done(
        turn_done, latency_ms=1, first_chunk_latency_ms=1
    )
    assert response["usage"] == usage.to_dict()


def test_parser_marks_non_object_tool_arguments_invalid() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            _chunk(
                tool_calls=[
                    _tool_delta(
                        call_id="call_array",
                        name="search",
                        arguments='["not", "an", "object"]',
                    )
                ],
                finish_reason="tool_calls",
            )
        )
    )
    events.extend(session.finalize())

    end = next(event for event in events if isinstance(event, ToolCallEnd))
    assert end.parsed_input is None
    assert end.parse_error == "tool arguments must decode to a JSON object"

    turn_done = next(event for event in events if isinstance(event, TurnDone))
    assert turn_done.tool_calls == []
    assert turn_done.invalid_tool_calls[0].raw_args == '["not", "an", "object"]'


def test_parser_isolates_invalid_and_valid_tool_calls_in_same_turn() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            _chunk(
                tool_calls=[
                    _tool_delta(
                        index=0,
                        call_id="call_bad",
                        name="search",
                        arguments='["not", "an", "object"]',
                    ),
                    _tool_delta(
                        index=1,
                        call_id="call_ok",
                        name="read_file",
                        arguments='{"path":"README.md"}',
                    ),
                ],
                finish_reason="tool_calls",
            )
        )
    )
    events.extend(session.finalize())

    turn_done = next(event for event in events if isinstance(event, TurnDone))

    assert len(turn_done.content) == 2
    assert isinstance(turn_done.content[0], InvalidToolCall)
    assert turn_done.content[0].id == "call_bad"
    assert isinstance(turn_done.content[1], ToolUseBlock)
    assert turn_done.content[1].id == "call_ok"
    assert turn_done.content[1].input == {"path": "README.md"}
    assert [tool.id for tool in turn_done.tool_calls] == ["call_ok"]
    assert [tool.id for tool in turn_done.invalid_tool_calls] == ["call_bad"]


def test_parser_preserves_invalid_tool_call_raw_arguments_in_legacy_output() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            _chunk(
                tool_calls=[
                    _tool_delta(
                        call_id="ask_1",
                        name="ask_user",
                        arguments='{"questions":',
                    )
                ],
                finish_reason="tool_calls",
            )
        )
    )
    events.extend(session.finalize())

    turn_done = next(event for event in events if isinstance(event, TurnDone))
    response = legacy_response_from_turn_done(
        turn_done, latency_ms=1, first_chunk_latency_ms=1
    )
    tool_use = response["content"][0]
    assert tool_use["input_parse_error"] is True
    assert tool_use["raw_args"] == '{"questions":'
    assert "parse_error" in tool_use
    assert tool_use["index"] == 0
    assert terminal_events_from_turn_done(turn_done)[0]["raw_args"] == '{"questions":'


def test_parser_finalize_on_error_preserves_partial_output() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(
            _chunk(
                reasoning="thinking ",
                content="partial ",
                tool_calls=[
                    _tool_delta(
                        call_id="call_partial",
                        name="search",
                        arguments='{"q"',
                    )
                ],
            )
        )
    )

    assert session.has_partial_output is True

    events.extend(session.finalize_on_error())

    end = next(event for event in events if isinstance(event, ToolCallEnd))
    assert end.call_id == "call_partial"
    assert end.parsed_input is None
    assert end.parse_error

    turn_done = next(event for event in events if isinstance(event, TurnDone))
    assert turn_done.stop_reason == "error"
    assert turn_done.raw_stop_reason == "error"
    assert turn_done.reasoning_blocks[0].text == "thinking "
    assert turn_done.text_blocks[0].text == "partial "
    assert [invalid.id for invalid in turn_done.invalid_tool_calls] == ["call_partial"]
    assert turn_done.tool_calls == []
    assert not any(isinstance(block, ToolUseBlock) for block in turn_done.content)
    assert list(session.finalize_on_error()) == []


def test_parser_keeps_legacy_tool_name_assignment_behavior() -> None:
    session = OpenAICompatParserSession()

    events = []
    events.extend(
        session.feed(_chunk(tool_calls=[_tool_delta(call_id="call_1", name="search")]))
    )
    events.extend(
        session.feed(_chunk(tool_calls=[_tool_delta(name="search", arguments='{"q"')]))
    )
    events.extend(
        session.feed(
            _chunk(
                tool_calls=[_tool_delta(arguments=':"abc"}')],
                finish_reason="tool_calls",
            )
        )
    )
    events.extend(session.finalize())

    name_events = [event for event in events if isinstance(event, ToolCallNameDelta)]
    assert [event.name_delta for event in name_events] == ["search", "search"]

    args_events = [event for event in events if isinstance(event, ToolCallArgsDelta)]
    assert [standard_event_to_legacy_delta(event) for event in args_events] == [
        {
            "type": "tool_use_delta",
            "tool_use_id": "call_1",
            "index": 0,
            "name_delta": None,
            "arguments_delta": '{"q"',
        },
        {
            "type": "tool_use_delta",
            "tool_use_id": "call_1",
            "index": 0,
            "name_delta": None,
            "arguments_delta": ':"abc"}',
        },
    ]

    end = next(event for event in events if isinstance(event, ToolCallEnd))
    assert end.name == "search"
    assert end.parsed_input == {"q": "abc"}
    turn_done = next(event for event in events if isinstance(event, TurnDone))
    response = legacy_response_from_turn_done(
        turn_done, latency_ms=1, first_chunk_latency_ms=1
    )
    assert response["stop_reason"] == "tool_calls"
    assert response["content"] == [
        {"type": "tool_use", "id": "call_1", "name": "search", "input": {"q": "abc"}}
    ]
