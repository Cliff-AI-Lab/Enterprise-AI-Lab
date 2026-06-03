from __future__ import annotations

from collections.abc import AsyncIterable, Iterable

from rd_agent_contracts import (
    AgentEvent,
    EventDraft,
    InvalidToolCall,
    TextBlock,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolObservabilityRecord,
    ToolUseBlock,
)
from rd_agent_core import CoreEventType, CoreEventWriter, CoreToolPolicy, TurnKernel, TurnRequest
from rd_llm_adapter import TextDelta, ToolCallArgsDelta, ToolCallEnd, ToolCallStart, TurnDone
from rd_llm_adapter.events import StandardEvent, UsageUpdate


class _InMemoryEventLog:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []
        self.idempotency: dict[tuple[str, str], AgentEvent] = {}

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        if idempotency_key is not None:
            existing = self.idempotency.get((run_id, idempotency_key))
            if existing is not None:
                return existing
        event = draft.to_event(
            run_id=run_id,
            seq=len(self.events) + 1,
            timestamp_ms=1710000000000 + len(self.events),
        )
        self.events.append(event)
        if idempotency_key is not None:
            self.idempotency[(run_id, idempotency_key)] = event
        return event

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]:
        events = [event for event in self.events if event.run_id == run_id and event.seq > from_seq]
        if limit is not None:
            return events[:limit]
        return events


class _LLMClient:
    def __init__(self, events: list[StandardEvent]) -> None:
        self.requests: list[TurnRequest] = []
        self._events = events

    async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
        self.requests.append(request)
        for event in self._events:
            yield event


class _ToolExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolExecutionRequest] = []

    def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        return ToolExecutionResult(ok=True, content=f"ran {request.tool_name}", duration_ms=3)


class _AsyncToolExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        return ToolExecutionResult(ok=True, content=f"async ran {request.tool_name}")


class _Observability:
    def __init__(self) -> None:
        self.records: list[ToolObservabilityRecord] = []

    def record_tool_calls(self, records: list[ToolObservabilityRecord]) -> None:
        self.records.extend(records)


class _CancellationToken:
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled

    def request_cancel(self) -> None:
        self.cancelled = True


def _request() -> TurnRequest:
    return TurnRequest(
        run_id="run-1",
        turn_id="turn-1",
        messages=[],
        tool_context=ToolExecutionContext(project_id="project-1", session_id="session-1"),
        model="test-model",
        turn_index=2,
    )


def _request_with_cancelled_token() -> TurnRequest:
    token = _CancellationToken()
    token.request_cancel()
    return TurnRequest(
        run_id="run-1",
        turn_id="turn-1",
        messages=[],
        tool_context=ToolExecutionContext(project_id="project-1"),
        cancellation_token=token,
    )


async def test_turn_kernel_streams_events_and_executes_completed_tool_call() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={"path": "README.md"})
    llm = _LLMClient(
        [
            TextDelta("checking"),
            ToolCallStart(index=0, call_id="tool-1", name="read_file"),
            ToolCallArgsDelta(index=0, call_id="tool-1", delta='{"path":"README.md"}'),
            ToolCallEnd(
                call_id="tool-1",
                name="read_file",
                index=0,
                encoding="native_json",
                raw_args='{"path":"README.md"}',
                parsed_input={"path": "README.md"},
                parse_error=None,
            ),
            UsageUpdate(
                input_tokens=7,
                output_tokens=11,
                total_tokens=18,
                cache_read_input_tokens=3,
                cache_creation_input_tokens=5,
            ),
            TurnDone(
                stop_reason="tool_use",
                content=[TextBlock("checking"), tool_call],
                text_blocks=[TextBlock("checking")],
                reasoning_blocks=[],
                tool_calls=[tool_call],
                invalid_tool_calls=[],
                usage=None,
                raw_stop_reason="tool_use",
            ),
        ]
    )
    log = _InMemoryEventLog()
    executor = _ToolExecutor()
    observability = _Observability()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(log, run_id="run-1"),
        tool_executor=executor,
        tool_observability=observability,
    )

    result = await kernel.run_turn(_request())

    assert result.stop_reason == "tool_use"
    assert result.usage.total() == 18
    assert result.usage.cache_read_input_tokens == 3
    assert result.usage.cache_creation_input_tokens == 5
    assert result.tool_calls_executed == 1
    assert executor.requests[0].tool_name == "read_file"
    assert executor.requests[0].turn == 2
    assert observability.records[0].tool_name == "read_file"
    assert [event.event_type for event in result.events] == [
        CoreEventType.TURN_STARTED,
        CoreEventType.TEXT_DELTA,
        CoreEventType.TOOL_CALL_STARTED,
        CoreEventType.TOOL_CALL_DELTA,
        CoreEventType.TOOL_CALL_COMPLETED,
        CoreEventType.USAGE_UPDATE,
        CoreEventType.TOOL_STARTED,
        CoreEventType.TOOL_COMPLETED,
        CoreEventType.TURN_COMPLETED,
    ]
    usage_event = next(
        event for event in result.events if event.event_type == CoreEventType.USAGE_UPDATE
    )
    assert usage_event.payload["usage_sequence"] == 1
    assert usage_event.payload["cache_read_input_tokens"] == 3
    assert usage_event.payload["cache_creation_input_tokens"] == 5


async def test_turn_kernel_returns_cancelled_without_streaming_when_token_is_cancelled() -> None:
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="end_turn",
                content=[TextBlock("should not stream")],
                text_blocks=[TextBlock("should not stream")],
                reasoning_blocks=[],
                tool_calls=[],
                invalid_tool_calls=[],
                raw_stop_reason="stop",
            )
        ]
    )
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
    )

    result = await kernel.run_turn(_request_with_cancelled_token())

    assert result.stop_reason == "cancelled"
    assert result.content == ()
    assert llm.requests == []
    assert [event.event_type for event in result.events] == [
        CoreEventType.TURN_STARTED,
        CoreEventType.TURN_COMPLETED,
    ]


async def test_turn_kernel_cancels_after_partial_stream_and_skips_tools() -> None:
    token = _CancellationToken()
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={"path": "README.md"})

    async def events(_request: TurnRequest) -> AsyncIterable[StandardEvent]:
        yield TextDelta("partial")
        token.request_cancel()
        yield TurnDone(
            stop_reason="tool_use",
            content=[tool_call],
            text_blocks=[],
            reasoning_blocks=[],
            tool_calls=[tool_call],
            invalid_tool_calls=[],
            raw_stop_reason="tool_use",
        )

    class _CancellingLLMClient:
        async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
            async for event in events(request):
                yield event

    executor = _ToolExecutor()
    kernel = TurnKernel(
        llm_client=_CancellingLLMClient(),
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
    )
    request = _request()
    request = TurnRequest(
        run_id=request.run_id,
        turn_id=request.turn_id,
        messages=request.messages,
        tool_context=request.tool_context,
        cancellation_token=token,
    )

    result = await kernel.run_turn(request)

    assert result.stop_reason == "cancelled"
    assert executor.requests == []
    assert CoreEventType.TEXT_DELTA in [event.event_type for event in result.events]


async def test_turn_kernel_marks_unexecuted_tools_cancelled_after_turn_done() -> None:
    token = _CancellationToken()
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={"path": "README.md"})

    class _CancellingAfterDoneLLMClient:
        async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
            yield TurnDone(
                stop_reason="tool_use",
                content=[tool_call],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[tool_call],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
            token.request_cancel()

    executor = _ToolExecutor()
    kernel = TurnKernel(
        llm_client=_CancellingAfterDoneLLMClient(),
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
    )

    result = await kernel.run_turn(
        TurnRequest(
            run_id="run-1",
            turn_id="turn-1",
            messages=[],
            tool_context=ToolExecutionContext(project_id="project-1"),
            cancellation_token=token,
        )
    )

    assert result.stop_reason == "cancelled"
    assert executor.requests == []
    assert len(result.content) == len(result.tool_results) == 1
    assert result.tool_results[0].error is not None
    assert result.tool_results[0].error["type"] == "cancelled"


async def test_turn_kernel_dedupes_usage_update_on_turn_retry() -> None:
    llm = _LLMClient(
        [
            UsageUpdate(input_tokens=2, output_tokens=3, total_tokens=5),
            TurnDone(
                stop_reason="stop",
                content=[TextBlock("done")],
                text_blocks=[TextBlock("done")],
                reasoning_blocks=[],
                tool_calls=[],
                invalid_tool_calls=[],
                raw_stop_reason="stop",
            ),
        ]
    )
    log = _InMemoryEventLog()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(log, run_id="run-1"),
    )

    await kernel.run_turn(_request())
    await kernel.run_turn(_request())

    usage_events = [
        event for event in log.events if event.event_type == CoreEventType.USAGE_UPDATE
    ]
    assert len(usage_events) == 1
    assert usage_events[0].payload["usage_sequence"] == 1


async def test_turn_kernel_awaits_async_tool_executor() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={"path": "README.md"})
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="tool_use",
                content=[tool_call],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[tool_call],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
        ]
    )
    executor = _AsyncToolExecutor()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
    )

    result = await kernel.run_turn(_request())

    assert executor.requests[0].tool_name == "read_file"
    assert result.tool_results[0].content == "async ran read_file"


async def test_turn_kernel_marks_configured_pause_tool_without_business_hardcoding() -> None:
    pause_tool = ToolUseBlock(
        id="tool-2",
        name="collect_user_confirmation",
        input={"question": "Continue?"},
    )
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="tool_use",
                content=[pause_tool],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[pause_tool],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
        ]
    )
    log = _InMemoryEventLog()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(log, run_id="run-1"),
        tool_executor=_ToolExecutor(),
        tool_policy=CoreToolPolicy(
            pause_tool_names=frozenset({"collect_user_confirmation"}),
            pause_stop_reason="waiting_for_user",
        ),
    )

    result = await kernel.run_turn(_request())

    assert result.pause_requested
    assert result.stop_reason == "waiting_for_user"
    assert CoreEventType.TURN_PAUSED in [event.event_type for event in result.events]


async def test_turn_kernel_skips_later_tools_after_pause_tool() -> None:
    pause_tool = ToolUseBlock(id="tool-1", name="ask_user", input={})
    write_tool = ToolUseBlock(id="tool-2", name="write_file", input={"path": "x"})
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="tool_use",
                content=[pause_tool, write_tool],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[pause_tool, write_tool],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
        ]
    )
    executor = _ToolExecutor()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        tool_policy=CoreToolPolicy(
            pause_tool_names=frozenset({"ask_user"}),
            pause_stop_reason="ask_user",
        ),
    )

    result = await kernel.run_turn(_request())

    assert [request.tool_name for request in executor.requests] == ["ask_user"]
    assert result.pause_requested
    assert len(result.tool_results) == 2
    assert result.tool_results[1].error is not None
    assert result.tool_results[1].error["type"] == "tool_skipped_after_pause"


async def test_turn_kernel_reports_invalid_tool_calls_without_execution() -> None:
    invalid = InvalidToolCall(
        id="tool-invalid",
        name="write_file",
        raw_args="{not-json",
        parse_error="invalid json",
        index=0,
    )
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="end_turn",
                content=[invalid],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[],
                invalid_tool_calls=[invalid],
                raw_stop_reason="end_turn",
            )
        ]
    )
    executor = _ToolExecutor()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
    )

    result = await kernel.run_turn(_request())

    assert result.invalid_tool_calls == (invalid,)
    assert executor.requests == []
    assert CoreEventType.TOOL_CALL_INVALID in [event.event_type for event in result.events]


async def test_turn_kernel_fails_closed_when_executor_is_missing() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="write_file", input={"path": "x"})
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="tool_use",
                content=[tool_call],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[tool_call],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
        ]
    )
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
    )

    result = await kernel.run_turn(_request())

    assert not result.tool_results[0].ok
    assert result.tool_results[0].error == {
        "type": "tool_executor_missing",
        "message": "No ToolExecutorPort was provided for tool execution.",
        "category": "tool_unavailable",
    }
    assert CoreEventType.TOOL_FAILED in [event.event_type for event in result.events]


async def test_turn_kernel_fails_closed_for_undeclared_tool_call() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="delete_project", input={"project_id": "p"})
    llm = _LLMClient(
        [
            TurnDone(
                stop_reason="tool_use",
                content=[tool_call],
                text_blocks=[],
                reasoning_blocks=[],
                tool_calls=[tool_call],
                invalid_tool_calls=[],
                raw_stop_reason="tool_use",
            )
        ]
    )
    executor = _ToolExecutor()
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
    )
    request = TurnRequest(
        run_id="run-1",
        turn_id="turn-1",
        messages=[],
        tool_context=ToolExecutionContext(project_id="project-1"),
        tools=(
            ToolDefinition(
                name="read_file",
                description="Read a file",
                input_schema={"type": "object"},
            ),
        ),
    )

    result = await kernel.run_turn(request)

    assert executor.requests == []
    assert not result.tool_results[0].ok
    assert result.tool_results[0].error == {
        "type": "tool_not_declared",
        "message": "Tool is not declared for this turn: delete_project",
        "category": "tool_unavailable",
    }


async def test_turn_kernel_rejects_run_id_drift_between_request_and_writer() -> None:
    llm = _LLMClient([])
    kernel = TurnKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
    )

    request = TurnRequest(
        run_id="run-2",
        turn_id="turn-1",
        messages=[],
        tool_context=ToolExecutionContext(project_id="project-1"),
    )

    try:
        await kernel.run_turn(request)
    except ValueError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("expected run_id drift validation failure")
