import pytest
from rd_agent_contracts import AgentEvent
from rd_replay_evals.recorder import RecordingEventSink, finalize_to_trace


@pytest.mark.asyncio
async def test_recorder_collects_events_in_order():
    sink = RecordingEventSink(run_id="run_rec")
    await sink.emit(
        AgentEvent(
            seq=1,
            timestamp_ms=1,
            run_id="run_rec",
            turn_id="t1",
            event_type="x",
            payload={},
        )
    )
    await sink.emit(
        AgentEvent(
            seq=2,
            timestamp_ms=2,
            run_id="run_rec",
            turn_id="t1",
            event_type="y",
            payload={},
        )
    )
    trace = finalize_to_trace(sink, category="chat")
    assert len(trace.events) == 2
    assert trace.events[0].seq == 1


@pytest.mark.asyncio
async def test_recorder_filters_other_runs():
    """recorder 必须只收自己 run_id 的 event，避免污染。"""
    sink = RecordingEventSink(run_id="run_rec")
    await sink.emit(
        AgentEvent(
            seq=1,
            timestamp_ms=1,
            run_id="run_other",
            turn_id="t1",
            event_type="x",
            payload={},
        )
    )
    await sink.emit(
        AgentEvent(
            seq=2,
            timestamp_ms=2,
            run_id="run_rec",
            turn_id="t1",
            event_type="y",
            payload={},
        )
    )
    trace = finalize_to_trace(sink, category="chat")
    assert len(trace.events) == 1
    assert trace.events[0].event_type == "y"
