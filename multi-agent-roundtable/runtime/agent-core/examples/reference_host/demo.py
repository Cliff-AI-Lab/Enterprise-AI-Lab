from __future__ import annotations

import asyncio
import json
from typing import Any

from rd_agent_contracts import (
    Message,
    RunBudget,
    RunCompletion,
    RunResultMetadata,
    RunScope,
    TextBlock,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolUseBlock,
)
from rd_agent_core import CoreEventWriter, RunKernel, RunLimits, RunRequest
from rd_agent_core.testing import (
    DeterministicIdGenerator,
    FunctionToolExecutor,
    ScriptedLLMClient,
)
from rd_llm_adapter import TurnDone, UsageUpdate

from .sqlite_reference_host import connect_sqlite_reference_host


async def run_demo() -> dict[str, Any]:
    host = connect_sqlite_reference_host()
    try:
        scope = RunScope(
            user_request_id="request-reference",
            project_id="project-reference",
            session_id="session-reference",
        )
        budget = RunBudget(
            max_turns=3,
            max_tool_calls=3,
            max_wall_clock_s=30,
            total_timeout_s=60,
        )
        run = host.persistence.create_root_run(
            run_id="run-reference",
            scope=scope,
            budget=budget,
        )
        host.persistence.mark_running(run.run_id)

        llm = ScriptedLLMClient([_tool_turn, _final_turn])
        kernel = RunKernel(
            llm_client=llm,
            event_writer=CoreEventWriter(host.event_log, run_id=run.run_id),
            tool_executor=FunctionToolExecutor({"lookup": _lookup}),
            id_generator=DeterministicIdGenerator(),
        )
        result = await kernel.run(
            RunRequest(
                run_id=run.run_id,
                messages=(
                    Message(
                        message_id="msg-user",
                        role="user",
                        content="lookup id 42",
                        turn_id="turn-0",
                    ),
                ),
                tool_context=ToolExecutionContext(
                    project_id=scope.project_id,
                    session_id=scope.session_id,
                    user_request_id=scope.user_request_id,
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
                model="reference-model",
                system_prompt="You are a deterministic reference host demo.",
                limits=RunLimits(max_turns=3, max_tool_calls=3, timeout_ms=30_000),
            )
        )
        completed = host.persistence.mark_completed(
            run.run_id,
            completion=RunCompletion(
                stop_reason=result.stop_reason,
                metadata=RunResultMetadata(
                    usage=result.usage,
                    turns_count=result.turns_count,
                    tool_calls_count=result.tool_calls_count,
                    extra={"event_count": len(result.events)},
                ),
            ),
        )
        if completed is None:
            raise RuntimeError("reference run disappeared")

        persisted_events = tuple(host.event_log.stream_events(run.run_id))
        return {
            "run_id": completed.run_id,
            "status": completed.status,
            "stop_reason": completed.stop_reason,
            "turns_count": completed.result_metadata.turns_count,
            "tool_calls_count": completed.result_metadata.tool_calls_count,
            "event_count": len(persisted_events),
            "event_types": [event.event_type for event in persisted_events],
        }
    finally:
        host.close()


def _tool_turn(_request: Any) -> list[Any]:
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


def _final_turn(request: Any) -> list[Any]:
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


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_demo()), ensure_ascii=False, indent=2))
