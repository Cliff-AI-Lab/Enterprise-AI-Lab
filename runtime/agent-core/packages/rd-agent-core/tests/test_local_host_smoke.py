from __future__ import annotations

import pytest
from rd_agent_contracts import (
    EventDraft,
    RunBudget,
    RunScope,
    RunStatus,
    TextBlock,
    ToolDefinition,
    ToolExecutionRequest,
    ToolUseBlock,
    Usage,
)
from rd_agent_core import CoreEventType
from rd_agent_core.testing import (
    AgentCoreHarness,
    DeterministicIdGenerator,
    FunctionToolExecutor,
    InMemoryEventLog,
    InMemoryRunPersistence,
    ScriptedLLMClient,
)
from rd_llm_adapter import TurnDone, UsageUpdate


def _tool_turn(_request) -> list:
    tool = ToolUseBlock(id="tool-1", name="lookup", input={"id": "42"})
    return [
        UsageUpdate(input_tokens=3, output_tokens=2, total_tokens=5),
        TurnDone(
            stop_reason="tool_use",
            content=[tool],
            text_blocks=[],
            reasoning_blocks=[],
            tool_calls=[tool],
            invalid_tool_calls=[],
            raw_stop_reason="tool_calls",
        ),
    ]


def _final_turn(request) -> list:
    latest_result = next(
        result
        for message in reversed(request.messages)
        for result in message.tool_results
        if message.role == "tool"
    )
    assert latest_result.content == "lookup:42"

    text = TextBlock("done")
    return [
        UsageUpdate(input_tokens=1, output_tokens=4, total_tokens=5),
        TurnDone(
            stop_reason="end_turn",
            content=[text],
            text_blocks=[text],
            reasoning_blocks=[],
            tool_calls=[],
            invalid_tool_calls=[],
            raw_stop_reason="stop",
        ),
    ]


def _lookup(request: ToolExecutionRequest) -> str:
    return f"{request.tool_name}:{request.tool_input['id']}"


async def test_local_host_harness_persists_kernel_result_and_events() -> None:
    llm = ScriptedLLMClient([_tool_turn, _final_turn])
    tools = (
        ToolDefinition(
            name="lookup",
            description="Lookup by id",
            input_schema={
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "required": ["id"],
            },
        ),
    )
    harness = AgentCoreHarness(
        llm_client=llm,
        tool_executor=FunctionToolExecutor({"lookup": _lookup}),
    )

    result = await harness.run(run_id="run-local", tools=tools)

    assert result.completed.status == RunStatus.COMPLETED
    assert result.completed.stop_reason == "end_turn"
    assert result.completed.result_metadata.usage == Usage(input_tokens=4, output_tokens=6)
    assert result.completed.result_metadata.turns_count == 2
    assert result.completed.result_metadata.tool_calls_count == 1
    assert result.completed.result_metadata.extra["event_count"] == len(
        result.kernel_result.events
    )
    assert len(llm.requests) == 2
    assert [event.seq for event in result.events] == list(range(1, len(result.events) + 1))
    assert [event.event_type for event in result.events].count(CoreEventType.TURN_COMPLETED) == 2
    assert any(event.event_type == CoreEventType.TOOL_COMPLETED for event in result.events)


def test_harness_event_log_preserves_idempotency() -> None:
    event_log = InMemoryEventLog()
    first = event_log.append_event(
        "run-1",
        draft=_draft("turn_started", {"attempt": 1}),
        idempotency_key="turn-1:start",
    )
    replay = event_log.append_event(
        "run-1",
        draft=_draft("turn_started", {"attempt": 2}),
        idempotency_key="turn-1:start",
    )

    assert replay == first
    assert replay.payload == {"attempt": 1}
    assert list(event_log.stream_events("run-1")) == [first]


def test_harness_run_persistence_links_continuations_to_parent() -> None:
    persistence = InMemoryRunPersistence()
    root = persistence.create_root_run(
        run_id="run-root",
        scope=RunScope(user_request_id="request-1", project_id="project-1"),
        budget=RunBudget(
            max_turns=2,
            max_tool_calls=2,
            max_wall_clock_s=30,
            total_timeout_s=60,
        ),
        max_continuations=1,
    )

    continuation = persistence.create_continuation_run(
        previous_run_id=root.run_id,
        engine_state_json='{"cursor":1}',
        run_id="run-cont-1",
    )
    overflow = persistence.create_continuation_run(
        previous_run_id="run-cont-1",
        engine_state_json='{"cursor":2}',
        run_id="run-cont-2",
    )

    assert continuation is not None
    assert continuation.status == RunStatus.PENDING
    assert continuation.scope.parent_run_id == root.run_id
    assert continuation.engine_state_json == '{"cursor":1}'
    assert persistence.load_run_with_parent("run-cont-1") == (continuation, root)
    assert overflow is None


def test_harness_run_persistence_rejects_duplicate_run_ids() -> None:
    persistence = InMemoryRunPersistence()
    budget = RunBudget(
        max_turns=2,
        max_tool_calls=2,
        max_wall_clock_s=30,
        total_timeout_s=60,
    )
    scope = RunScope(user_request_id="request-1", project_id="project-1")

    persistence.create_root_run(run_id="run-1", scope=scope, budget=budget)

    with pytest.raises(ValueError, match="run_id already exists"):
        persistence.create_root_run(run_id="run-1", scope=scope, budget=budget)


async def test_harness_default_run_ids_do_not_reuse_event_streams() -> None:
    harness = AgentCoreHarness(
        llm_client=ScriptedLLMClient([_final_turn_without_tool, _final_turn_without_tool]),
        id_generator=DeterministicIdGenerator(),
    )

    first = await harness.run()
    second = await harness.run()

    assert first.run.run_id == "run-1"
    assert second.run.run_id == "run-2"
    assert {event.run_id for event in first.events} == {"run-1"}
    assert {event.run_id for event in second.events} == {"run-2"}
    assert first.events[0].seq == 1
    assert second.events[0].seq == 1


def _draft(event_type: str, payload: dict):
    return EventDraft(event_type=event_type, payload=payload, turn_id="turn-1")


def _final_turn_without_tool(_request) -> list:
    text = TextBlock("done")
    return [
        TurnDone(
            stop_reason="end_turn",
            content=[text],
            text_blocks=[text],
            reasoning_blocks=[],
            tool_calls=[],
            invalid_tool_calls=[],
            raw_stop_reason="stop",
        )
    ]
