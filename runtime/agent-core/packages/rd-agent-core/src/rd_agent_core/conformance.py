"""Executable conformance checks for host port implementations."""

from __future__ import annotations

import inspect
import uuid

from rd_agent_contracts import (
    AgentEvent,
    EventDraft,
    EventLogPort,
    RunBudget,
    RunCompletion,
    RunPersistencePort,
    RunRecord,
    RunScope,
    RunStatus,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
)

from .turn import ToolExecutorLike


def assert_event_log_port_conformance(
    event_log: EventLogPort,
    *,
    run_id: str | None = None,
) -> tuple[AgentEvent, ...]:
    resolved_run_id = run_id or f"conformance-run-{uuid.uuid4()}"
    first = event_log.append_event(
        resolved_run_id,
        EventDraft(event_type="turn_started", payload={"attempt": 1}, turn_id="turn-1"),
        idempotency_key="turn-1:start",
    )
    replay = event_log.append_event(
        resolved_run_id,
        EventDraft(event_type="turn_started", payload={"attempt": 2}, turn_id="turn-1"),
        idempotency_key="turn-1:start",
    )
    second = event_log.append_event(
        resolved_run_id,
        EventDraft(event_type="turn_completed", payload={"ok": True}, turn_id="turn-1"),
    )
    events = tuple(event_log.stream_events(resolved_run_id))

    if replay != first:
        raise AssertionError("EventLogPort must return the original event for idempotent replay")
    if [event.seq for event in events] != [first.seq, second.seq]:
        raise AssertionError("EventLogPort.stream_events must preserve per-run event order")
    if tuple(event_log.stream_events(resolved_run_id, from_seq=first.seq)) != (second,):
        raise AssertionError("EventLogPort.stream_events(from_seq=...) must be exclusive")
    return events


def assert_run_persistence_port_conformance(
    persistence: RunPersistencePort,
    *,
    run_id: str | None = None,
) -> tuple[RunRecord, ...]:
    resolved_run_id = run_id or f"conformance-run-{uuid.uuid4()}"
    budget = RunBudget(
        max_turns=2,
        max_tool_calls=2,
        max_wall_clock_s=30,
        total_timeout_s=60,
    )
    root = persistence.create_root_run(
        run_id=resolved_run_id,
        scope=RunScope(user_request_id=f"request-{uuid.uuid4()}", project_id="project-1"),
        budget=budget,
        max_continuations=1,
    )
    running = persistence.mark_running(root.run_id)
    completed = persistence.mark_completed(
        root.run_id,
        completion=RunCompletion(stop_reason="end_turn"),
    )
    continuation = persistence.create_continuation_run(
        previous_run_id=root.run_id,
        engine_state_json='{"cursor":1}',
        run_id=f"{resolved_run_id}-cont-1",
    )
    overflow = persistence.create_continuation_run(
        previous_run_id=continuation.run_id if continuation is not None else root.run_id,
        engine_state_json='{"cursor":2}',
        run_id=f"{resolved_run_id}-cont-2",
    )

    if running is None or running.status != RunStatus.RUNNING:
        raise AssertionError("RunPersistencePort.mark_running must return a running record")
    if completed is None or completed.status != RunStatus.COMPLETED:
        raise AssertionError("RunPersistencePort.mark_completed must return a completed record")
    if continuation is None or continuation.scope.parent_run_id != root.run_id:
        raise AssertionError("RunPersistencePort must link continuation runs to their parent")
    if overflow is not None:
        raise AssertionError("RunPersistencePort must enforce max_continuations")
    loaded = persistence.load_run_with_parent(continuation.run_id)
    if loaded != (continuation, completed):
        raise AssertionError("RunPersistencePort.load_run_with_parent must include parent run")
    return (root, running, completed, continuation)


async def assert_tool_executor_port_conformance(
    executor: ToolExecutorLike,
    *,
    request: ToolExecutionRequest | None = None,
) -> ToolExecutionResult:
    resolved_request = request or ToolExecutionRequest(
        tool_name="conformance_echo",
        tool_input={"value": "ok"},
        context=ToolExecutionContext(project_id="project-1"),
        tool_use_id="tool-1",
        turn=1,
    )
    raw_result = executor.execute_tool(resolved_request)
    result = await raw_result if inspect.isawaitable(raw_result) else raw_result
    if not isinstance(result, ToolExecutionResult):
        raise AssertionError("ToolExecutorPort.execute_tool must return ToolExecutionResult")
    if result.error is not None and not isinstance(result.error, dict):
        raise AssertionError("ToolExecutionResult.error must be a dict when present")
    return result
