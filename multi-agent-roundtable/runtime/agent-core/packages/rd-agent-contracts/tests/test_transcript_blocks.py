"""contracts 1.2 typed transcript blocks 测试。

字段定义跟随 model_adapter v8 真实实现（codesphere-saas messages.py），
让 rd-llm-adapter 移植时 messages.py 可纯 re-export。
"""
from dataclasses import FrozenInstanceError

import pytest
from rd_agent_contracts import (
    InvalidToolCall,
    ProviderState,
    ReasoningBlock,
    StandardToolCall,
    TextBlock,
    ToolUseBlock,
)


def test_text_block_is_frozen():
    block = TextBlock(text="hello")
    assert block.text == "hello"
    assert block.type == "text"
    assert block.provider_data is None
    with pytest.raises(FrozenInstanceError):
        block.text = "modified"  # type: ignore[misc]


def test_text_block_with_provider_data():
    block = TextBlock(text="hello", provider_data={"cache": True})
    assert block.provider_data == {"cache": True}


def test_reasoning_block_with_signature():
    block = ReasoningBlock(
        text="thinking...",
        signature="sig-abc",
        redacted=False,
    )
    assert block.text == "thinking..."
    assert block.signature == "sig-abc"
    assert block.redacted is False
    assert block.type == "reasoning"


def test_reasoning_block_redacted_data():
    """Anthropic redacted_thinking 用 data 字段而非 text。"""
    block = ReasoningBlock(
        text="",
        data="encrypted-blob-base64",
        redacted=True,
    )
    assert block.redacted is True
    assert block.data == "encrypted-blob-base64"
    assert block.signature is None


def test_reasoning_block_requires_redacted_data_invariant():
    with pytest.raises(ValueError, match="requires data"):
        ReasoningBlock(redacted=True)

    with pytest.raises(ValueError, match="only valid"):
        ReasoningBlock(data="encrypted-blob-base64")


def test_tool_use_block_basic():
    block = ToolUseBlock(
        id="toolu_abc",
        name="run_command",
        input={"command": "ls"},
    )
    assert block.id == "toolu_abc"
    assert block.name == "run_command"
    assert block.input == {"command": "ls"}
    assert block.type == "tool_use"


def test_tool_use_block_default_input():
    """默认 input={}，便于解析增量场景。"""
    block = ToolUseBlock(id="t1", name="x")
    assert block.input == {}


def test_invalid_tool_call_carries_error():
    block = InvalidToolCall(
        id="toolu_xyz",
        name="run_com",
        raw_args="{ ",
        parse_error="JSON truncated",
        index=0,
        encoding="native_json",
    )
    assert block.parse_error == "JSON truncated"
    assert block.encoding == "native_json"
    assert block.type == "invalid_tool_call"


def test_invalid_tool_call_encoding_optional():
    block = InvalidToolCall(
        id="t1",
        name="x",
        raw_args="",
        parse_error="empty",
        index=0,
    )
    assert block.encoding is None


def test_standard_tool_call_basic():
    """StandardToolCall 是 adapter 已确认 complete 的 tool call。"""
    call = StandardToolCall(
        id="toolu_xyz",
        name="run_command",
        input={"command": "ls"},
    )
    assert call.encoding == "native_json"  # default


def test_standard_tool_call_custom_encoding():
    call = StandardToolCall(
        id="t1",
        name="x",
        input={},
        encoding="xml",
    )
    assert call.encoding == "xml"


def test_provider_state_is_dict():
    state = ProviderState(data={"some_key": "some_val"})
    assert state.data["some_key"] == "some_val"


def test_provider_state_default_empty():
    state = ProviderState()
    assert state.data == {}


def test_blocks_can_be_listed_in_content():
    """Message.content 可 list[StandardContentBlock]，与 TurnDone.content 一致。"""
    blocks: list = [
        TextBlock(text="hello"),
        ReasoningBlock(text="thinking", signature="sig"),
        ToolUseBlock(id="t1", name="ls", input={}),
    ]
    assert len(blocks) == 3
    assert isinstance(blocks[0], TextBlock)
    assert isinstance(blocks[1], ReasoningBlock)
    assert isinstance(blocks[2], ToolUseBlock)
