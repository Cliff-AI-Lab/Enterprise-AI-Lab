from io import StringIO

import pytest
from rd_agent_contracts import AgentEvent
from rd_replay_evals.trace_format import (
    GoldenTrace,
    TraceMeta,
    read_trace,
    write_trace,
)


def test_write_then_read_round_trip():
    meta = TraceMeta(
        trace_id="t1",
        recorded_at_ms=1714377600000,
        category="single_tool",
        run_id="run_1",
        schema_version="1.0.0",
        tags=["p9", "minimal"],
    )
    events = [
        AgentEvent(
            seq=1,
            timestamp_ms=1,
            run_id="run_1",
            turn_id="turn_1",
            event_type="message_start",
            payload={},
        ),
        AgentEvent(
            seq=2,
            timestamp_ms=2,
            run_id="run_1",
            turn_id="turn_1",
            event_type="tool_use",
            payload={"tool_use_id": "tu_1"},
        ),
    ]
    trace = GoldenTrace(meta=meta, events=events)

    buf = StringIO()
    write_trace(trace, buf)
    buf.seek(0)
    loaded = read_trace(buf)

    assert loaded.meta.trace_id == "t1"
    assert len(loaded.events) == 2
    assert loaded.events[1].payload["tool_use_id"] == "tu_1"


def test_event_seq_must_be_monotonic():
    """trace 加载时校验 seq 单调。"""
    meta = TraceMeta(
        trace_id="t2",
        recorded_at_ms=1,
        category="x",
        run_id="r",
        schema_version="1.0.0",
        tags=[],
    )
    events = [
        AgentEvent(
            seq=1,
            timestamp_ms=1,
            run_id="r",
            turn_id="t",
            event_type="x",
            payload={},
        ),
        AgentEvent(
            seq=3,
            timestamp_ms=2,
            run_id="r",
            turn_id="t",
            event_type="x",
            payload={},
        ),
        AgentEvent(
            seq=2,
            timestamp_ms=3,
            run_id="r",
            turn_id="t",
            event_type="x",
            payload={},
        ),
    ]
    with pytest.raises(ValueError, match="seq.*monotonic"):
        GoldenTrace(meta=meta, events=events)
