"""Canonical runtime event helpers for host-neutral agent kernels."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any

from rd_agent_contracts import AgentEvent, EventDraft, EventLogPort


class CoreEventType(StrEnum):
    TURN_STARTED = "turn_started"
    TEXT_DELTA = "text_delta"
    REASONING_DELTA = "reasoning_delta"
    TOOL_CALL_STARTED = "tool_call_started"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    TOOL_CALL_INVALID = "tool_call_invalid"
    USAGE_UPDATE = "usage_update"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    TOOL_FAILED = "tool_failed"
    TURN_PAUSED = "turn_paused"
    TURN_COMPLETED = "turn_completed"


@dataclass(frozen=True)
class CoreEventWriter:
    """Small append-only facade over ``EventLogPort``.

    The writer owns no persistence, transport, tenant, or UI assumptions. Hosts
    allocate event sequence numbers through their ``EventLogPort`` implementation.
    """

    event_log: EventLogPort
    run_id: str
    turn_id: str = ""
    idempotency_prefix: str | None = None

    def with_turn(self, turn_id: str) -> CoreEventWriter:
        return replace(self, turn_id=turn_id)

    def append(
        self,
        event_type: CoreEventType | str,
        payload: Mapping[str, Any] | None = None,
        *,
        turn_id: str | None = None,
        message_id: str | None = None,
        action_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        resolved_key = self._resolve_idempotency_key(idempotency_key)
        draft = EventDraft(
            event_type=str(event_type),
            payload=dict(payload or {}),
            turn_id=self.turn_id if turn_id is None else turn_id,
            message_id=message_id,
            action_id=action_id,
        )
        return self.event_log.append_event(
            self.run_id,
            draft,
            idempotency_key=resolved_key,
        )

    def _resolve_idempotency_key(self, key: str | None) -> str | None:
        if key is None:
            return None
        if not self.idempotency_prefix:
            return key
        return f"{self.idempotency_prefix}:{key}"
