from __future__ import annotations

import pytest
from rd_agent_contracts import (
    RunBudget,
    RunScope,
    RunStatus,
    TextBlock,
    ToolDefinition,
    ToolExecutionRequest,
    ToolUseBlock,
)
from rd_agent_core import AgentRunner, AgentRunnerRequest
from rd_agent_core.testing import (
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
    text = TextBlock(f"done: {latest_result.content}")
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
    return f"lookup:{request.tool_input['id']}"


class _RunObserver:
    def __init__(self) -> None:
        self.summaries = []

    def record_run_summary(self, summary) -> None:
        self.summaries.append(summary)


async def test_agent_runner_persists_run_lifecycle_and_kernel_result() -> None:
    persistence = InMemoryRunPersistence()
    event_log = InMemoryEventLog()
    observer = _RunObserver()
    runner = AgentRunner(
        run_persistence=persistence,
        event_log=event_log,
        llm_client=ScriptedLLMClient([_tool_turn, _final_turn]),
        tool_executor=FunctionToolExecutor({"lookup": _lookup}),
        run_observer=observer,
        id_generator=DeterministicIdGenerator(),
    )

    result = await runner.run(
        AgentRunnerRequest(
            run_id="run-agent",
            scope=RunScope(user_request_id="request-1", project_id="project-1"),
            budget=RunBudget(
                max_turns=3,
                max_tool_calls=3,
                max_wall_clock_s=30,
                total_timeout_s=60,
            ),
            tools=(
                ToolDefinition(
                    name="lookup",
                    description="Lookup by id",
                    input_schema={
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                        "required": ["id"],
                    },
                ),
            ),
        )
    )

    assert result.completed.status == RunStatus.COMPLETED
    assert result.completed.stop_reason == "end_turn"
    assert result.completed.result_metadata.turns_count == 2
    assert result.completed.result_metadata.tool_calls_count == 1
    assert result.completed.result_metadata.extra["event_count"] == len(
        result.kernel_result.events
    )
    assert result.summary.run_id == "run-agent"
    assert result.summary.stop_reason == "end_turn"
    assert result.summary.turns_count == 2
    assert result.summary.tool_calls_count == 1
    assert result.summary.total_tokens == 10
    assert result.summary.output_text == "done: lookup:42"
    assert observer.summaries == [result.summary]
    assert [event.seq for event in result.events] == list(range(1, len(result.events) + 1))


async def test_agent_runner_marks_failed_when_kernel_raises() -> None:
    persistence = InMemoryRunPersistence()
    event_log = InMemoryEventLog()
    observer = _RunObserver()
    runner = AgentRunner(
        run_persistence=persistence,
        event_log=event_log,
        llm_client=ScriptedLLMClient([]),
        run_observer=observer,
        id_generator=DeterministicIdGenerator(),
    )

    with pytest.raises(RuntimeError, match="no scripted LLM turn"):
        await runner.run(
            AgentRunnerRequest(
                run_id="run-failed",
                scope=RunScope(user_request_id="request-1", project_id="project-1"),
                budget=RunBudget(
                    max_turns=1,
                    max_tool_calls=1,
                    max_wall_clock_s=30,
                    total_timeout_s=60,
                ),
            )
        )

    failed = persistence.load_run("run-failed")
    assert failed is not None
    assert failed.status == RunStatus.FAILED
    assert "no scripted LLM turn" in str(failed.error_message)
    assert observer.summaries[0].status == "failed"
    assert "no scripted LLM turn" in str(observer.summaries[0].error_message)
