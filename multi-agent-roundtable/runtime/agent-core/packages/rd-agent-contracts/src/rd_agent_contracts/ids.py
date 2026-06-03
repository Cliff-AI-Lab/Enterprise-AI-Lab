"""Agent Runtime ID 类型与生成器。

所有 ID 是 NewType-ish 的 str 别名（运行时是 str，类型系统区分）。
IdGenerator 是 Protocol，默认实现 UuidIdGenerator 用 uuid4 + 前缀。
"""
from __future__ import annotations

import uuid
from typing import NewType, Protocol

RunId = NewType("RunId", str)
TurnId = NewType("TurnId", str)
MessageId = NewType("MessageId", str)
ActionId = NewType("ActionId", str)
ToolUseId = NewType("ToolUseId", str)
SessionId = NewType("SessionId", str)


class IdGenerator(Protocol):
    """ID 生成 protocol。Phase A 默认实现 UuidIdGenerator。"""

    def run_id(self) -> RunId: ...
    def turn_id(self) -> TurnId: ...
    def message_id(self) -> MessageId: ...
    def action_id(self) -> ActionId: ...
    def tool_use_id(self) -> ToolUseId: ...
    def session_id(self) -> SessionId: ...


class UuidIdGenerator:
    """uuid4 + 前缀的默认实现。"""

    def run_id(self) -> RunId:
        return RunId(f"run_{uuid.uuid4()}")

    def turn_id(self) -> TurnId:
        return TurnId(f"turn_{uuid.uuid4()}")

    def message_id(self) -> MessageId:
        return MessageId(f"msg_{uuid.uuid4()}")

    def action_id(self) -> ActionId:
        return ActionId(f"act_{uuid.uuid4()}")

    def tool_use_id(self) -> ToolUseId:
        return ToolUseId(f"tu_{uuid.uuid4()}")

    def session_id(self) -> SessionId:
        return SessionId(f"sess_{uuid.uuid4()}")
