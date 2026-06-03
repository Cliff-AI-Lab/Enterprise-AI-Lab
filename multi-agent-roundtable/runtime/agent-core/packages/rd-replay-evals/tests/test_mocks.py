import pytest
from rd_agent_contracts import AgentEvent
from rd_replay_evals.mocks import MockLLMProvider, MockToolExecutor
from rd_replay_evals.trace_format import GoldenTrace, TraceMeta


@pytest.mark.asyncio
async def test_mock_llm_replays_chunks_in_order():
    """MockLLMProvider 按 trace 录制顺序重放 chunk。"""
    trace = GoldenTrace(
        meta=TraceMeta(
            trace_id="t",
            recorded_at_ms=0,
            category="chat",
            run_id="r",
            schema_version="1.0.0",
            tags=[],
        ),
        events=[
            AgentEvent(
                seq=1,
                timestamp_ms=1,
                run_id="r",
                turn_id="t",
                event_type="text_delta",
                payload={"text": "hello"},
            ),
            AgentEvent(
                seq=2,
                timestamp_ms=2,
                run_id="r",
                turn_id="t",
                event_type="text_delta",
                payload={"text": " world"},
            ),
        ],
    )
    p = MockLLMProvider(trace)
    chunks = []
    async for c in p.stream_chunks(turn_id="t"):
        chunks.append(c)
    assert [c.payload["text"] for c in chunks] == ["hello", " world"]


@pytest.mark.asyncio
async def test_mock_tool_executor_returns_recorded_result():
    trace = GoldenTrace(
        meta=TraceMeta(
            trace_id="t",
            recorded_at_ms=0,
            category="single_tool",
            run_id="r",
            schema_version="1.0.0",
            tags=[],
        ),
        events=[
            AgentEvent(
                seq=1,
                timestamp_ms=1,
                run_id="r",
                turn_id="t",
                event_type="tool_completed",
                payload={
                    "tool_use_id": "tu_1",
                    "output": "file contents",
                    "ok": True,
                },
            ),
        ],
    )
    e = MockToolExecutor(trace)
    result = await e.execute(
        tool_use_id="tu_1", tool_name="read_file", tool_input={"path": "x"}
    )
    assert result["ok"] is True
    assert result["output"] == "file contents"


@pytest.mark.asyncio
async def test_mock_tool_executor_unknown_tool_use_id_raises():
    trace = GoldenTrace(
        meta=TraceMeta(
            trace_id="t",
            recorded_at_ms=0,
            category="x",
            run_id="r",
            schema_version="1.0.0",
            tags=[],
        ),
        events=[],
    )
    e = MockToolExecutor(trace)
    with pytest.raises(KeyError, match="tu_unknown"):
        await e.execute(
            tool_use_id="tu_unknown", tool_name="x", tool_input={}
        )
