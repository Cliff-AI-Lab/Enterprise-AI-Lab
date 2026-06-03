"""TurnDone derived 字段一致性合约测试（rd-llm-adapter 1.0.1）。

events.py TurnDone docstring 声明：text_blocks / reasoning_blocks / tool_calls /
invalid_tool_calls 是 content 的 derived 视图，**必须**可由 content 通过类型过滤完整重建。

本测试不直接调 LLM provider（那是 fixture replay 测试的事），只构造合成 TurnDone 实例验证
derived 字段语义。adapter 实现新 provider 时也应保证此一致性。
"""

from __future__ import annotations

from rd_agent_contracts import (
    InvalidToolCall,
    ReasoningBlock,
    TextBlock,
    ToolUseBlock,
)
from rd_llm_adapter import TurnDone, UsageUpdate


def _build_turn_done() -> TurnDone:
    text_a = TextBlock(text="hello")
    reasoning = ReasoningBlock(text="think...", signature="sig-1")
    tool_use = ToolUseBlock(
        id="call_1",
        name="bash",
        input={"command": "ls"},
    )
    invalid = InvalidToolCall(
        id="call_2",
        name="bash",
        raw_args="{not-json",
        parse_error="invalid json",
        index=0,
    )
    text_b = TextBlock(text="done")
    content = [text_a, reasoning, tool_use, invalid, text_b]

    return TurnDone(
        stop_reason="end_turn",
        content=content,
        text_blocks=[b for b in content if isinstance(b, TextBlock)],
        reasoning_blocks=[b for b in content if isinstance(b, ReasoningBlock)],
        tool_calls=[b for b in content if isinstance(b, ToolUseBlock)],
        invalid_tool_calls=[b for b in content if isinstance(b, InvalidToolCall)],
        usage=UsageUpdate(input_tokens=10, output_tokens=20, total_tokens=30),
        raw_stop_reason="end_turn",
    )


def test_text_blocks_derives_from_content() -> None:
    turn = _build_turn_done()
    expected = [b for b in turn.content if isinstance(b, TextBlock)]
    assert turn.text_blocks == expected
    assert len(turn.text_blocks) == 2


def test_reasoning_blocks_derives_from_content() -> None:
    turn = _build_turn_done()
    expected = [b for b in turn.content if isinstance(b, ReasoningBlock)]
    assert turn.reasoning_blocks == expected
    assert len(turn.reasoning_blocks) == 1


def test_tool_calls_derives_from_content() -> None:
    turn = _build_turn_done()
    expected = [b for b in turn.content if isinstance(b, ToolUseBlock)]
    assert turn.tool_calls == expected
    assert len(turn.tool_calls) == 1


def test_invalid_tool_calls_derives_from_content() -> None:
    turn = _build_turn_done()
    expected = [b for b in turn.content if isinstance(b, InvalidToolCall)]
    assert turn.invalid_tool_calls == expected
    assert len(turn.invalid_tool_calls) == 1


def test_content_order_preserved() -> None:
    """content 是有序的 transcript truth，derived 字段不破坏 content 内顺序。"""
    turn = _build_turn_done()
    # content 内 text 块的顺序应与 text_blocks 一致
    text_blocks_in_content_order = [b for b in turn.content if isinstance(b, TextBlock)]
    assert turn.text_blocks == text_blocks_in_content_order
    # 块的相对顺序与 content 一致
    assert turn.text_blocks[0].text == "hello"
    assert turn.text_blocks[1].text == "done"
