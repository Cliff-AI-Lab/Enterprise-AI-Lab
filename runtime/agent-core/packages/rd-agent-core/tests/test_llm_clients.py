from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from rd_agent_contracts import (
    Message,
    TextBlock,
    ToolCall,
    ToolCallStatus,
    ToolDefinition,
    ToolExecutionContext,
    ToolResult,
    ToolUseBlock,
)
from rd_agent_core import (
    AnthropicNativeLLMClient,
    OpenAICompatLLMClient,
    ProviderClientConfig,
    TurnRequest,
)
from rd_llm_adapter import TextDelta, TurnDone


class FakeTransport:
    def __init__(self, chunks: list[Any]) -> None:
        self.chunks = chunks
        self.requests: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []

    async def stream(
        self,
        request_body: dict[str, Any],
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        extra_headers: dict[str, str] | None = None,
    ) -> AsyncIterator[Any]:
        self.requests.append(request_body)
        self.calls.append(
            {
                "api_key": api_key,
                "base_url": base_url,
                "timeout": timeout,
                "extra_headers": extra_headers,
            }
        )
        for chunk in self.chunks:
            if isinstance(chunk, Exception):
                raise chunk
            yield chunk


def _turn_request(messages: tuple[Message, ...] = ()) -> TurnRequest:
    return TurnRequest(
        run_id="run-1",
        turn_id="turn-1",
        messages=messages,
        tool_context=ToolExecutionContext(project_id="project-1"),
        model=None,
        system_prompt="sys",
        tools=(
            ToolDefinition(
                name="lookup",
                description="Lookup by id",
                input_schema={"type": "object", "properties": {}},
            ),
        ),
        turn_index=1,
    )


async def test_openai_compat_llm_client_streams_standard_events() -> None:
    transport = FakeTransport(
        [
            {"choices": [{"delta": {"content": "hel"}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "lo"}, "finish_reason": "stop"}]},
        ]
    )
    client = OpenAICompatLLMClient(
        ProviderClientConfig(
            model="model-default",
            api_key="key",
            base_url="https://example.test/v1",
            extra_headers={"x-test": "1"},
        ),
        transport=transport,
    )

    events = [event async for event in client.stream_turn(_turn_request())]

    assert [event.text for event in events if isinstance(event, TextDelta)] == [
        "hel",
        "lo",
    ]
    done = next(event for event in events if isinstance(event, TurnDone))
    assert done.stop_reason == "stop"
    assert done.text_blocks[0] == TextBlock("hello")
    assert transport.requests[0]["model"] == "model-default"
    assert transport.requests[0]["messages"][0] == {"role": "system", "content": "sys"}
    assert transport.calls[0]["extra_headers"] == {"x-test": "1"}


async def test_openai_compat_llm_client_serializes_tool_result_messages() -> None:
    transport = FakeTransport(
        [{"choices": [{"delta": {"content": "done"}, "finish_reason": "stop"}]}]
    )
    client = OpenAICompatLLMClient(
        ProviderClientConfig(model="model-default", api_key="key", base_url="base"),
        transport=transport,
    )
    assistant = Message(
        message_id="msg-assistant",
        role="assistant",
        content=[
            ToolUseBlock(id="tool-1", name="lookup", input={"id": "42"}).__dict__,
        ],
        turn_id="turn-0",
        tool_calls=[
            ToolCall(
                tool_use_id="tool-1",
                tool_name="lookup",
                input={"id": "42"},
                status=ToolCallStatus.COMPLETE,
            )
        ],
    )
    tool = Message(
        message_id="msg-tool",
        role="tool",
        content="lookup:42",
        turn_id="turn-0",
        tool_results=[ToolResult(tool_use_id="tool-1", ok=True, content="lookup:42")],
    )

    _ = [event async for event in client.stream_turn(_turn_request((assistant, tool)))]

    assert transport.requests[0]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "tool-1",
        "content": "lookup:42",
    }


async def test_openai_compat_llm_client_recovers_partial_error_output() -> None:
    transport = FakeTransport(
        [
            {"choices": [{"delta": {"content": "partial"}, "finish_reason": None}]},
            RuntimeError("stream failed"),
        ]
    )
    client = OpenAICompatLLMClient(
        ProviderClientConfig(model="model-default", api_key="key", base_url="base"),
        transport=transport,
    )

    events = [event async for event in client.stream_turn(_turn_request())]

    done = next(event for event in events if isinstance(event, TurnDone))
    assert done.stop_reason == "error"
    assert done.text_blocks[0] == TextBlock("partial")


async def test_openai_compat_llm_client_reraises_error_without_partial_output() -> None:
    transport = FakeTransport([RuntimeError("stream failed")])
    client = OpenAICompatLLMClient(
        ProviderClientConfig(model="model-default", api_key="key", base_url="base"),
        transport=transport,
    )

    with pytest.raises(RuntimeError, match="stream failed"):
        _ = [event async for event in client.stream_turn(_turn_request())]


async def test_anthropic_native_llm_client_streams_standard_events() -> None:
    transport = FakeTransport(
        [
            {"type": "message_start", "message": {"usage": {"input_tokens": 1}}},
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "hello"},
            },
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
            {"type": "message_stop"},
        ]
    )
    client = AnthropicNativeLLMClient(
        ProviderClientConfig(
            model="claude",
            api_key="key",
            base_url="https://api.anthropic.com",
        ),
        transport=transport,
        thinking_budget_tokens=128,
    )

    events = [event async for event in client.stream_turn(_turn_request())]

    done = next(event for event in events if isinstance(event, TurnDone))
    assert done.stop_reason == "stop"
    assert done.text_blocks[0] == TextBlock("hello")
    assert transport.requests[0]["thinking"] == {
        "type": "enabled",
        "budget_tokens": 128,
    }
