from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest
from rd_llm_adapter.anthropic_native import (
    AnthropicNativeAdapter,
)
from rd_llm_adapter.events import TurnDone
from rd_llm_adapter.messages import (
    InvalidToolCall,
    ReasoningBlock,
    TextBlock,
    ToolUseBlock,
)

DEFAULT_ANTHROPIC_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "anthropic_native"


def _anthropic_fixture_paths() -> list[Path]:
    fixture_dir = Path(
        os.getenv(
            "ANTHROPIC_NATIVE_FIXTURES_DIR",
            str(DEFAULT_ANTHROPIC_FIXTURE_DIR),
        )
    )
    if not fixture_dir.exists():
        return []
    return sorted(fixture_dir.glob("*.json"))


def _load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _turn_done_snapshot(turn_done: TurnDone) -> dict[str, Any]:
    return {
        "stop_reason": turn_done.stop_reason,
        "raw_stop_reason": turn_done.raw_stop_reason,
        "usage": turn_done.usage.to_dict() if turn_done.usage else {},
        "content": [_content_block_snapshot(block) for block in turn_done.content],
        "tool_calls": [
            {
                "id": tool_call.id,
                "name": tool_call.name,
                "input": tool_call.input,
                "encoding": tool_call.encoding,
            }
            for tool_call in turn_done.tool_calls
        ],
        "invalid_tool_calls": [
            _content_block_snapshot(block) for block in turn_done.invalid_tool_calls
        ],
    }


def _content_block_snapshot(block: Any) -> dict[str, Any]:
    if isinstance(block, ReasoningBlock):
        return {
            "type": "reasoning",
            "text": block.text,
            "signature": block.signature,
            "redacted": block.redacted,
            "data": block.data,
        }
    if isinstance(block, TextBlock):
        return {"type": "text", "text": block.text}
    if isinstance(block, ToolUseBlock):
        return {
            "type": "tool_use",
            "id": block.id,
            "name": block.name,
            "input": block.input,
        }
    if isinstance(block, InvalidToolCall):
        return {
            "type": "invalid_tool_call",
            "id": block.id,
            "name": block.name,
            "raw_args": block.raw_args,
            "parse_error": block.parse_error,
            "index": block.index,
            "encoding": block.encoding,
        }
    raise AssertionError(f"unsupported content block: {block!r}")


@pytest.mark.parametrize("path", _anthropic_fixture_paths(), ids=lambda p: p.name)
def test_anthropic_native_request_fixtures_match_snapshots(path: Path) -> None:
    fixture = _load_fixture(path)
    request_case = fixture.get("request")
    if not request_case:
        pytest.skip(f"{path} has no request case")

    request_body = AnthropicNativeAdapter().build_request(**request_case["input"])

    assert request_body == request_case["expected_body"]


@pytest.mark.parametrize("path", _anthropic_fixture_paths(), ids=lambda p: p.name)
def test_anthropic_native_stream_fixtures_match_snapshots(path: Path) -> None:
    fixture = _load_fixture(path)
    stream_case = fixture.get("stream")
    if not stream_case:
        pytest.skip(f"{path} has no stream case")

    session = AnthropicNativeAdapter().create_parser_session()
    turn_done: TurnDone | None = None
    for raw_chunk in stream_case["raw_chunks"]:
        for event in session.feed(raw_chunk):
            if isinstance(event, TurnDone):
                turn_done = event
    if turn_done is None:
        for event in session.finalize():
            if isinstance(event, TurnDone):
                turn_done = event

    assert turn_done is not None
    assert _turn_done_snapshot(turn_done) == stream_case["expected_turn_done"]
