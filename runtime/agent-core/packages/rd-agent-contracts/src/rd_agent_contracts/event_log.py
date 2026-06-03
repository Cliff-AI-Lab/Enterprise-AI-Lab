"""Host-neutral event log port."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from .events import AgentEvent, EventDraft


@runtime_checkable
class EventLogPort(Protocol):
    """Append-only AgentEvent log.

    Implementations allocate monotonically increasing per-run ``seq`` values.
    If ``idempotency_key`` is provided, replaying the same append must return
    the original AgentEvent without writing a duplicate.
    """

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent: ...

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]: ...
