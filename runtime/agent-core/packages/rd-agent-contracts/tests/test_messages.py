import pytest
from rd_agent_contracts.enums import ToolCallStatus
from rd_agent_contracts.messages import Message, ToolCall, ToolResult


def test_message_basic():
    msg = Message(
        message_id="msg_1",
        role="user",
        content="hello",
        turn_id="turn_1",
    )
    assert msg.role == "user"
    assert msg.content == "hello"


def test_message_role_validation():
    with pytest.raises(ValueError, match="role"):
        Message(message_id="msg_1", role="invalid", content="x", turn_id="turn_1")


def test_tool_call_status_required():
    """每个 tool_call 必须显式标 status。"""
    tc = ToolCall(
        tool_use_id="tu_1",
        tool_name="read_file",
        input={"path": "/etc/hosts"},
        status=ToolCallStatus.COMPLETE,
    )
    assert tc.status is ToolCallStatus.COMPLETE


def test_tool_call_partial_not_executable():
    tc = ToolCall(
        tool_use_id="tu_2",
        tool_name="read_file",
        input={},
        status=ToolCallStatus.PARTIAL,
    )
    assert tc.status.is_executable() is False


def test_tool_result_pairs_with_tool_use_id():
    """tool_result.tool_use_id 必须匹配某个 tool_call.tool_use_id。"""
    tr = ToolResult(
        tool_use_id="tu_1",
        ok=True,
        content="ok",
        error=None,
    )
    assert tr.tool_use_id == "tu_1"


def test_tool_result_error_when_not_ok():
    tr = ToolResult(
        tool_use_id="tu_1",
        ok=False,
        content="",
        error={"type": "timeout", "message": "exec timed out after 300s"},
    )
    assert tr.ok is False
    assert tr.error["type"] == "timeout"
