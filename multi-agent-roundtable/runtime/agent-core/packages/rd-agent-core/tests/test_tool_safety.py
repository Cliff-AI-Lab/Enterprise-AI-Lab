from __future__ import annotations

from rd_agent_contracts import (
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolUseBlock,
)
from rd_agent_core import (
    CoreEventWriter,
    CoreToolPolicy,
    ToolSafetyPolicy,
    TurnKernel,
    TurnRequest,
)
from rd_agent_core.testing import FunctionToolExecutor, InMemoryEventLog, ScriptedLLMClient
from rd_llm_adapter import TurnDone


def _tool_turn(tool_name: str = "write_file") -> list:
    tool = ToolUseBlock(id="tool-1", name=tool_name, input={"path": "x"})
    return [
        TurnDone(
            stop_reason="tool_use",
            content=[tool],
            text_blocks=[],
            reasoning_blocks=[],
            tool_calls=[tool],
            invalid_tool_calls=[],
            raw_stop_reason="tool_calls",
        )
    ]


def _ok_tool(_request: ToolExecutionRequest) -> str:
    return "ok"


async def test_tool_safety_blocks_named_tool_before_executor_runs() -> None:
    executor = FunctionToolExecutor({"write_file": _ok_tool})
    kernel = TurnKernel(
        llm_client=ScriptedLLMClient([_tool_turn()]),
        event_writer=CoreEventWriter(InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        tool_policy=CoreToolPolicy(
            safety_policy=ToolSafetyPolicy(blocked_tool_names=frozenset({"write_file"}))
        ),
    )

    result = await kernel.run_turn(_request())

    assert not result.tool_results[0].ok
    assert result.tool_results[0].error is not None
    assert result.tool_results[0].error["type"] == "tool_blocked"
    assert executor.requests == []


async def test_tool_safety_enforces_allowlist() -> None:
    kernel = TurnKernel(
        llm_client=ScriptedLLMClient([_tool_turn("shell")]),
        event_writer=CoreEventWriter(InMemoryEventLog(), run_id="run-1"),
        tool_executor=FunctionToolExecutor({"shell": _ok_tool}),
        tool_policy=CoreToolPolicy(
            safety_policy=ToolSafetyPolicy(allowed_tool_names=frozenset({"read_file"}))
        ),
    )

    result = await kernel.run_turn(
        _request(
            tools=(
                ToolDefinition(
                    name="shell",
                    description="Run shell",
                    input_schema={"type": "object"},
                ),
            )
        )
    )

    assert result.tool_results[0].error is not None
    assert result.tool_results[0].error["type"] == "tool_not_allowed"


async def test_tool_safety_requires_confirmation_for_mutating_tools() -> None:
    executor = FunctionToolExecutor({"write_file": _ok_tool})
    kernel = TurnKernel(
        llm_client=ScriptedLLMClient([_tool_turn()]),
        event_writer=CoreEventWriter(InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        tool_policy=CoreToolPolicy(
            safety_policy=ToolSafetyPolicy(
                require_confirmation_for_mutating_tools=True
            )
        ),
    )

    result = await kernel.run_turn(_request())

    assert result.tool_results[0].error is not None
    assert result.tool_results[0].error["type"] == "tool_confirmation_required"
    assert executor.requests == []


async def test_tool_safety_executes_confirmed_mutating_tool() -> None:
    executor = FunctionToolExecutor({"write_file": _ok_tool})
    kernel = TurnKernel(
        llm_client=ScriptedLLMClient([_tool_turn()]),
        event_writer=CoreEventWriter(InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        tool_policy=CoreToolPolicy(
            safety_policy=ToolSafetyPolicy(
                require_confirmation_for_mutating_tools=True,
                confirmed_tool_use_ids=frozenset({"tool-1"}),
            )
        ),
    )

    result = await kernel.run_turn(_request())

    assert result.tool_results[0].ok
    assert result.tool_results[0].content == "ok"
    assert [request.tool_name for request in executor.requests] == ["write_file"]


def _request(
    *,
    tools: tuple[ToolDefinition, ...] | None = None,
) -> TurnRequest:
    return TurnRequest(
        run_id="run-1",
        turn_id="turn-1",
        messages=(),
        tool_context=ToolExecutionContext(project_id="project-1"),
        tools=tools
        or (
            ToolDefinition(
                name="write_file",
                description="Write file",
                input_schema={"type": "object"},
                mutates_workspace=True,
            ),
        ),
        turn_index=1,
    )
