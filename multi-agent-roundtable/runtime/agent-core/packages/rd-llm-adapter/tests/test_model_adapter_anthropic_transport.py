from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from rd_llm_adapter.anthropic_transport import (
    anthropic_messages_url,
    iter_anthropic_sse_json,
)


async def _lines(items: list[str]) -> AsyncIterator[str]:
    for item in items:
        yield item


def test_anthropic_messages_url_normalizes_api_roots() -> None:
    assert anthropic_messages_url("") == "https://api.anthropic.com/v1/messages"
    assert (
        anthropic_messages_url("https://api.anthropic.com")
        == "https://api.anthropic.com/v1/messages"
    )
    assert (
        anthropic_messages_url("https://api.anthropic.com/v1")
        == "https://api.anthropic.com/v1/messages"
    )
    assert (
        anthropic_messages_url("https://api.anthropic.com/v1/messages")
        == "https://api.anthropic.com/v1/messages"
    )


@pytest.mark.asyncio
async def test_iter_anthropic_sse_json_parses_events_and_data() -> None:
    events = [
        event
        async for event in iter_anthropic_sse_json(
            _lines(
                [
                    "event: message_start",
                    'data: {"message":{"usage":{"input_tokens":1}}}',
                    "",
                    ": keepalive",
                    "event: content_block_delta",
                    'data: {"type":"content_block_delta","index":0,',
                    'data: "delta":{"type":"text_delta","text":"hi"}}',
                    "",
                    "event: ping",
                    'data: {"type":"ping"}',
                    "",
                    "data: [DONE]",
                    "",
                ]
            )
        )
    ]

    assert events == [
        {"type": "message_start", "message": {"usage": {"input_tokens": 1}}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "hi"},
        },
        {"type": "ping"},
    ]


@pytest.mark.asyncio
async def test_iter_anthropic_sse_json_flushes_final_event_without_blank_line() -> None:
    events = [
        event
        async for event in iter_anthropic_sse_json(
            _lines(["event: message_stop", 'data: {"type":"message_stop"}'])
        )
    ]

    assert events == [{"type": "message_stop"}]
