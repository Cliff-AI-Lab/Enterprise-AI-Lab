from rd_agent_contracts.enums import StopReason, ToolCallStatus


def test_stop_reason_values():
    """覆盖 codesphere-saas 现有所有 stop_reason。"""
    assert StopReason.END_TURN.value == "end_turn"
    assert StopReason.MAX_TURNS.value == "max_turns"
    assert StopReason.MAX_TOOL_CALLS.value == "max_tool_calls"
    assert StopReason.MAX_WALL_CLOCK.value == "max_wall_clock"
    assert StopReason.ASK_USER.value == "ask_user"
    assert StopReason.CANCELLED.value == "cancelled"
    assert StopReason.ERROR.value == "error"
    assert StopReason.LOOP_BREAK_NO_PROGRESS.value == "loop_break:no_progress"
    assert StopReason.LOOP_BREAK_REPEAT.value == "loop_break:repeat"


def test_tool_call_status_values():
    """partial / complete / invalid — partial 和 invalid 永不执行（P5 规则）。"""
    assert ToolCallStatus.PARTIAL.value == "partial"
    assert ToolCallStatus.COMPLETE.value == "complete"
    assert ToolCallStatus.INVALID.value == "invalid"


def test_tool_call_status_executable():
    """只有 COMPLETE 可执行；这是 P5 规则的契约表达。"""
    assert ToolCallStatus.COMPLETE.is_executable() is True
    assert ToolCallStatus.PARTIAL.is_executable() is False
    assert ToolCallStatus.INVALID.is_executable() is False
