import json

import pytest
from rd_agent_contracts import SCHEMA_VERSION
from rd_agent_contracts.events import AgentEvent, EventDraft


def test_agent_event_minimal():
    e = AgentEvent(
        seq=1,
        timestamp_ms=1714377600000,
        run_id="run_123",
        turn_id="turn_1",
        event_type="message_delta",
        payload={"text": "hello"},
    )
    assert e.seq == 1
    assert e.schema_version == SCHEMA_VERSION


def test_agent_event_seq_must_be_positive():
    with pytest.raises(ValueError, match="seq"):
        AgentEvent(
            seq=0,
            timestamp_ms=1,
            run_id="run_x",
            turn_id="turn_x",
            event_type="x",
            payload={},
        )


def test_agent_event_explicit_schema_version():
    e = AgentEvent(
        seq=1,
        timestamp_ms=1,
        run_id="run_x",
        turn_id="turn_x",
        event_type="x",
        payload={},
        schema_version="0.9.0",
    )
    assert e.schema_version == "0.9.0"


def test_agent_event_serializable():
    """envelope 必须可以 JSON 序列化（用于 trace 文件）。"""
    e = AgentEvent(
        seq=1,
        timestamp_ms=1714377600000,
        run_id="run_123",
        turn_id="turn_1",
        event_type="tool_use",
        payload={"tool_use_id": "tu_1", "tool_name": "read_file"},
    )
    s = json.dumps(e.to_dict())
    parsed = json.loads(s)
    assert parsed["seq"] == 1
    assert parsed["payload"]["tool_use_id"] == "tu_1"


def test_event_draft_explicit_schema_version():
    draft = EventDraft(
        event_type="x",
        payload={},
        schema_version="0.9.0",
    )

    event = draft.to_event(run_id="run_x", seq=1, timestamp_ms=1)

    assert event.schema_version == "0.9.0"
