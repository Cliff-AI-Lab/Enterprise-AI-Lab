from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from rd_agent_contracts import SCHEMA_VERSION
from rd_agent_contracts.event_log import EventLogPort
from rd_agent_contracts.events import AgentEvent, EventDraft


class _InMemoryEventLogPort:
    def __init__(self) -> None:
        self._lock = Lock()
        self._events: dict[str, list[AgentEvent]] = {}
        self._idempotency: dict[tuple[str, str], AgentEvent] = {}
        self._clock_ms = 1710000000000

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        with self._lock:
            if idempotency_key:
                existing = self._idempotency.get((run_id, idempotency_key))
                if existing:
                    return existing

            events = self._events.setdefault(run_id, [])
            event = draft.to_event(
                run_id=run_id,
                seq=len(events) + 1,
                timestamp_ms=draft.timestamp_ms or self._clock_ms,
            )
            events.append(event)
            self._clock_ms += 1

            if idempotency_key:
                self._idempotency[(run_id, idempotency_key)] = event
            return event

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]:
        with self._lock:
            events = [
                event
                for event in self._events.get(run_id, [])
                if event.seq > from_seq
            ]
            if limit is not None:
                events = events[:limit]
            return list(events)


def test_event_draft_builds_agent_event_with_assigned_sequence():
    draft = EventDraft(
        event_type="message_delta",
        payload={"text": "hello"},
        turn_id="turn_1",
    )

    event = draft.to_event(run_id="run_1", seq=1, timestamp_ms=1710000000000)

    assert event.seq == 1
    assert event.run_id == "run_1"
    assert event.turn_id == "turn_1"
    assert event.schema_version == SCHEMA_VERSION
    assert event.payload == {"text": "hello"}


def test_event_draft_rejects_empty_event_type():
    try:
        EventDraft(event_type="", payload={})
    except ValueError as exc:
        assert "event_type" in str(exc)
    else:
        raise AssertionError("expected event_type validation failure")


def test_event_log_port_protocol_is_runtime_checkable():
    port: EventLogPort = _InMemoryEventLogPort()

    assert isinstance(port, EventLogPort)


def test_event_log_append_assigns_monotonic_seq_under_concurrency():
    port = _InMemoryEventLogPort()

    def append(i: int) -> int:
        event = port.append_event(
            "run_1",
            EventDraft(event_type="delta", payload={"i": i}),
        )
        return event.seq

    with ThreadPoolExecutor(max_workers=8) as pool:
        seqs = list(pool.map(append, range(40)))

    streamed = list(port.stream_events("run_1"))

    assert sorted(seqs) == list(range(1, 41))
    assert [event.seq for event in streamed] == list(range(1, 41))


def test_event_log_idempotency_key_replays_without_duplicate_append():
    port = _InMemoryEventLogPort()

    first = port.append_event(
        "run_1",
        EventDraft(event_type="tool_use", payload={"tool": "read_file"}),
        idempotency_key="turn_1:tool_1:start",
    )
    replay = port.append_event(
        "run_1",
        EventDraft(event_type="tool_use", payload={"tool": "write_file"}),
        idempotency_key="turn_1:tool_1:start",
    )

    assert replay == first
    assert replay.payload == {"tool": "read_file"}
    assert [event.seq for event in port.stream_events("run_1")] == [1]


def test_event_log_stream_events_resumes_after_from_seq_and_honors_limit():
    port = _InMemoryEventLogPort()
    for i in range(5):
        port.append_event("run_1", EventDraft(event_type="delta", payload={"i": i}))

    resumed = list(port.stream_events("run_1", from_seq=2, limit=2))

    assert [event.seq for event in resumed] == [3, 4]
