"""StopReason / ToolCallStatus 枚举。"""
from __future__ import annotations

from enum import StrEnum


class StopReason(StrEnum):
    """Engine turn loop 的所有终止原因。

    覆盖 codesphere-saas agent_runner/types.py + loop_guards.py 现有所有值。
    """

    END_TURN = "end_turn"
    MAX_TURNS = "max_turns"
    MAX_TOOL_CALLS = "max_tool_calls"
    MAX_WALL_CLOCK = "max_wall_clock"
    ASK_USER = "ask_user"
    CANCELLED = "cancelled"
    ERROR = "error"
    LOOP_BREAK_NO_PROGRESS = "loop_break:no_progress"
    LOOP_BREAK_REPEAT = "loop_break:repeat"


class ToolCallStatus(StrEnum):
    """Tool call 状态。

    P5 engine 唯一规则：只有 COMPLETE 才可执行。PARTIAL（length 截断未闭合）
    和 INVALID（schema 不合法）永不执行——这是 contracts 的硬约束。
    """

    PARTIAL = "partial"
    COMPLETE = "complete"
    INVALID = "invalid"

    def is_executable(self) -> bool:
        return self is ToolCallStatus.COMPLETE
