from __future__ import annotations

from collections.abc import Iterable

from rd_agent_contracts import AgentEvent, EventDraft
from rd_agent_core import CoreEventType, CoreEventWriter


class _InMemoryEventLog:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self.idempotency: dict[tuple[str, str], AgentEvent] = {}

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        if idempotency_key is not None:
            existing = self.idempotency.get((run_id, idempotency_key))
            if existing is not None:
                return existing
        event = draft.to_event(
            run_id=run_id,
            seq=len(self.events) + 1,
            timestamp_ms=1710000000000 + len(self.events),
        )
        self.events.append(event)
        if idempotency_key is not None:
            self.idempotency[(run_id, idempotency_key)] = event
        return event

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]:
        events = [event for event in self.events if event.run_id == run_id and event.seq > from_seq]
        if limit is not None:
            return events[:limit]
        return events


def test_core_event_writer_appends_canonical_event_with_turn_context() -> None:
    log = _InMemoryEventLog()
    writer = CoreEventWriter(log, run_id="run-1").with_turn("turn-1")

    event = writer.append(CoreEventType.TEXT_DELTA, {"text": "hello"})

    assert event.seq == 1
    assert event.run_id == "run-1"
    assert event.turn_id == "turn-1"
    assert event.event_type == "text_delta"
    assert event.payload == {"text": "hello"}


def test_core_event_writer_preserves_idempotency_boundary() -> None:
    log = _InMemoryEventLog()
    writer = CoreEventWriter(log, run_id="run-1", idempotency_prefix="core")

    first = writer.append(CoreEventType.TURN_STARTED, {"attempt": 1}, idempotency_key="start")
    replay = writer.append(CoreEventType.TURN_STARTED, {"attempt": 2}, idempotency_key="start")

    assert replay == first
    assert replay.payload == {"attempt": 1}
    assert list(log.stream_events("run-1")) == [first]
    assert ("run-1", "core:start") in log.idempotency
