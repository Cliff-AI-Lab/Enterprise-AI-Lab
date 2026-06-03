from __future__ import annotations

from rd_agent_contracts import ToolExecutionRequest
from rd_agent_core.conformance import (
    assert_event_log_port_conformance,
    assert_run_persistence_port_conformance,
    assert_tool_executor_port_conformance,
)
from rd_agent_core.testing import (
    FunctionToolExecutor,
    InMemoryEventLog,
    InMemoryRunPersistence,
)


def test_event_log_conformance_accepts_in_memory_port() -> None:
    events = assert_event_log_port_conformance(InMemoryEventLog())

    assert [event.seq for event in events] == [1, 2]


def test_run_persistence_conformance_accepts_in_memory_port() -> None:
    records = assert_run_persistence_port_conformance(InMemoryRunPersistence())

    assert [record.status for record in records[1:3]] == ["running", "completed"]


async def test_tool_executor_conformance_accepts_function_executor() -> None:
    executor = FunctionToolExecutor({"conformance_echo": lambda request: "ok"})

    result = await assert_tool_executor_port_conformance(executor)

    assert result.ok
    assert result.content == "ok"
    assert isinstance(executor.requests[0], ToolExecutionRequest)
