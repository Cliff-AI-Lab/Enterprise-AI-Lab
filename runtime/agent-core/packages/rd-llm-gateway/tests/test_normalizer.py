from rd_agent_contracts import ToolCallStatus, Usage
from rd_llm_gateway.normalizer import StreamNormalizer
from rd_llm_gateway.types import StreamChunkType


def test_normalizer_assigns_seq():
    """normalizer 自己负责发 seq，不信 provider 的。"""
    n = StreamNormalizer()
    c1 = n.text_delta("hello")
    c2 = n.text_delta(" world")
    assert c1.seq == 1
    assert c2.seq == 2


def test_normalizer_tool_use_complete():
    n = StreamNormalizer()
    n.text_delta("thinking...")
    c = n.tool_use_complete(
        tool_use_id="tu_1",
        tool_name="read_file",
        tool_input_json='{"path": "/etc/hosts"}',
    )
    assert c.chunk_type is StreamChunkType.TOOL_USE
    assert c.tool_call_status is ToolCallStatus.COMPLETE


def test_normalizer_tool_use_partial_on_length_stop():
    """关键 invariant：length 截断时，partial json 必须标 PARTIAL，不可标 COMPLETE。"""
    n = StreamNormalizer()
    c = n.tool_use_partial(
        tool_use_id="tu_2",
        tool_name="write_file",
        tool_input_partial_json='{"path": "/tmp/x", "content": "unfinis',
    )
    assert c.tool_call_status is ToolCallStatus.PARTIAL
    assert not c.tool_call_status.is_executable()


def test_normalizer_tool_use_invalid_json():
    """非法 JSON 必须标 INVALID。"""
    n = StreamNormalizer()
    c = n.tool_use_invalid(
        tool_use_id="tu_3",
        tool_name="read_file",
        raw="{invalid json}",
    )
    assert c.tool_call_status is ToolCallStatus.INVALID
    assert not c.tool_call_status.is_executable()


def test_normalizer_usage_missing_returns_zero():
    n = StreamNormalizer()
    c = n.usage(None)
    assert c.usage == Usage()


def test_normalizer_usage_partial_fields():
    n = StreamNormalizer()
    c = n.usage({"input_tokens": 100})
    assert c.usage.input_tokens == 100
    assert c.usage.output_tokens == 0
