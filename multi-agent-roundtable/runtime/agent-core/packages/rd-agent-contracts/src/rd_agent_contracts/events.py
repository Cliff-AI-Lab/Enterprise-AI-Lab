"""AgentEvent — engine 与外部之间的统一事件 envelope。

强约束：
- seq 单调递增（>=1），P2 normalizer 拒绝乱序
- schema_version 默认 canonical（与 __init__.SCHEMA_VERSION 同值），边界 adapter 做 up/down grade
- payload 任意 JSON 兼容 dict
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ._version import SCHEMA_VERSION as _DEFAULT_SCHEMA_VERSION


@dataclass(frozen=True)
class AgentEvent:
    seq: int
    timestamp_ms: int
    run_id: str
    turn_id: str
    event_type: str
    payload: dict[str, Any]
    schema_version: str = field(default=_DEFAULT_SCHEMA_VERSION)
    message_id: str | None = None
    action_id: str | None = None

    def __post_init__(self) -> None:
        if self.seq < 1:
            raise ValueError(f"seq must be >= 1, got {self.seq}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventDraft:
    """Event payload before the host assigns run-local sequence.

    EventLogPort implementations allocate ``seq`` and may fill ``timestamp_ms``
    when the draft leaves it unset.
    """

    event_type: str
    payload: dict[str, Any]
    turn_id: str = ""
    timestamp_ms: int | None = None
    schema_version: str = field(default=_DEFAULT_SCHEMA_VERSION)
    message_id: str | None = None
    action_id: str | None = None

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type must be non-empty")

    def to_event(
        self,
        *,
        run_id: str,
        seq: int,
        timestamp_ms: int,
    ) -> AgentEvent:
        return AgentEvent(
            seq=seq,
            timestamp_ms=timestamp_ms,
            run_id=run_id,
            turn_id=self.turn_id,
            event_type=self.event_type,
            payload=dict(self.payload),
            schema_version=self.schema_version,
            message_id=self.message_id,
            action_id=self.action_id,
        )
