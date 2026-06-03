"""测试 OpenAI-compat adapter 解析 SSE 并产出归一化 StreamChunk。"""
from rd_agent_contracts import ToolCallStatus
from rd_llm_gateway.adapters.openai_compat import parse_openai_sse_chunk
from rd_llm_gateway.normalizer import StreamNormalizer
from rd_llm_gateway.types import StreamChunkType


def test_parse_text_delta():
    """OpenAI: data: {choices:[{delta:{content:hello}}]}"""
    raw = {
        "id": "chatcmpl-1",
        "object": "chat.completion.chunk",
        "choices": [
            {"delta": {"content": "hello"}, "index": 0, "finish_reason": None}
        ],
    }
    n = StreamNormalizer()
    chunks = parse_openai_sse_chunk(raw, n)
    assert len(chunks) == 1
    assert chunks[0].chunk_type is StreamChunkType.TEXT_DELTA
    assert chunks[0].text == "hello"


def test_parse_tool_call_complete():
    """完整 tool_call。"""
    raw = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "tu_1",
                            "type": "function",
                            "function": {
                                "name": "read_file",
                                "arguments": '{"path":"/etc/hosts"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
    }
    n = StreamNormalizer()
    chunks = parse_openai_sse_chunk(raw, n)
    tc = [c for c in chunks if c.chunk_type is StreamChunkType.TOOL_USE]
    assert len(tc) == 1
    assert tc[0].tool_call_status is ToolCallStatus.COMPLETE


def test_parse_tool_call_partial_on_length():
    """finish_reason=length + 未闭合 args -> PARTIAL。"""
    raw = {
        "choices": [
            {
                "delta": {
                    "tool_calls": [
                        {
                            "index": 0,
                            "id": "tu_2",
                            "function": {
                                "name": "write_file",
                                "arguments": '{"path":"/tmp/x","content":"unf',
                            },
                        }
                    ],
                },
                "finish_reason": "length",
            }
        ],
    }
    n = StreamNormalizer()
    chunks = parse_openai_sse_chunk(raw, n)
    tc = [c for c in chunks if c.chunk_type is StreamChunkType.TOOL_USE]
    assert tc[0].tool_call_status is ToolCallStatus.PARTIAL


def test_parse_usage_chunk():
    raw = {
        "choices": [{"delta": {}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
    }
    n = StreamNormalizer()
    chunks = parse_openai_sse_chunk(raw, n)
    u = [c for c in chunks if c.chunk_type is StreamChunkType.USAGE]
    assert len(u) == 1
    assert u[0].usage.input_tokens == 100
    assert u[0].usage.output_tokens == 50
