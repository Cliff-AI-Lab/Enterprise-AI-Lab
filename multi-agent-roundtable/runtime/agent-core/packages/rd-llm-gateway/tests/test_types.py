import pytest
from rd_agent_contracts import ToolCallStatus, Usage
from rd_llm_gateway.types import ChatRequest, StreamChunk, StreamChunkType


def test_chat_request_minimal():
    req = ChatRequest(
        model="claude-sonnet-4-20250514",
        messages=[{"role": "user", "content": "hello"}],
        tools=[],
        max_tokens=4096,
    )
    assert req.model == "claude-sonnet-4-20250514"


def test_stream_chunk_text_delta():
    c = StreamChunk(
        seq=1,
        chunk_type=StreamChunkType.TEXT_DELTA,
        text="hello",
    )
    assert c.chunk_type is StreamChunkType.TEXT_DELTA


def test_stream_chunk_tool_use():
    c = StreamChunk(
        seq=2,
        chunk_type=StreamChunkType.TOOL_USE,
        tool_use_id="tu_1",
        tool_name="read_file",
        tool_input_partial='{"path": "/etc/hosts"}',
        tool_call_status=ToolCallStatus.COMPLETE,
    )
    assert c.tool_call_status is ToolCallStatus.COMPLETE


def test_stream_chunk_partial_tool_use_marked():
    """length 截断时，normalizer 必须标 PARTIAL（不修复）。"""
    c = StreamChunk(
        seq=3,
        chunk_type=StreamChunkType.TOOL_USE,
        tool_use_id="tu_2",
        tool_name="write_file",
        tool_input_partial='{"path": "/tmp/x", "content": "hello',
        tool_call_status=ToolCallStatus.PARTIAL,
    )
    assert c.tool_call_status is ToolCallStatus.PARTIAL
    assert not c.tool_call_status.is_executable()


def test_stream_chunk_usage_at_end():
    c = StreamChunk(
        seq=99,
        chunk_type=StreamChunkType.USAGE,
        usage=Usage(input_tokens=100, output_tokens=50),
    )
    assert c.usage.total() == 150


def test_stream_chunk_seq_must_be_positive():
    with pytest.raises(ValueError, match="seq"):
        StreamChunk(seq=0, chunk_type=StreamChunkType.TEXT_DELTA, text="x")
