from __future__ import annotations

from collections.abc import AsyncIterable, Iterable

from rd_agent_contracts import (
    AgentEvent,
    EventDraft,
    MessageId,
    RunId,
    SessionId,
    TextBlock,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolUseBlock,
    ToolUseId,
    TurnId,
)
from rd_agent_core import (
    CoreEventWriter,
    CoreToolPolicy,
    RunKernel,
    RunLimits,
    RunRequest,
    build_messages_after_turn,
)
from rd_llm_adapter import TextDelta, TurnDone, UsageUpdate
from rd_llm_adapter.events import StandardEvent


class _Ids:
    def __init__(self) -> None:
        self.turns = 0
        self.messages = 0

    def run_id(self) -> RunId:
        return RunId("run-fixed")

    def turn_id(self) -> TurnId:
        self.turns += 1
        return TurnId(f"turn-{self.turns}")

    def message_id(self) -> MessageId:
        self.messages += 1
        return MessageId(f"msg-{self.messages}")

    def action_id(self):
        return "act-fixed"

    def tool_use_id(self) -> ToolUseId:
        return ToolUseId("tool-fixed")

    def session_id(self) -> SessionId:
        return SessionId("session-fixed")


class _InMemoryEventLog:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent:
        event = draft.to_event(
            run_id=run_id,
            seq=len(self.events) + 1,
            timestamp_ms=1710000000000 + len(self.events),
        )
        self.events.append(event)
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
    def __init__(self, turns: list[list[StandardEvent]]) -> None:
        self.turns = turns
        self.requests = []

    async def stream_turn(self, request) -> AsyncIterable[StandardEvent]:
        self.requests.append(request)
        for event in self.turns[len(self.requests) - 1]:
            yield event


class _ToolExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        return ToolExecutionResult(ok=True, content=f"result:{request.tool_name}")


class _CancellationToken:
    def __init__(self) -> None:
        self.cancelled = False

    def is_cancelled(self) -> bool:
        return self.cancelled

    def request_cancel(self) -> None:
        self.cancelled = True


def _request(**overrides) -> RunRequest:
    values = {
        "run_id": "run-1",
        "messages": (),
        "tool_context": ToolExecutionContext(project_id="project-1"),
        "tools": (
            ToolDefinition(
                name="read_file",
                description="Read file",
                input_schema={"type": "object"},
            ),
        ),
    }
    values.update(overrides)
    return RunRequest(**values)


async def test_run_kernel_stops_after_text_only_turn() -> None:
    llm = _LLMClient(
        [
            [
                TextDelta("hello"),
                UsageUpdate(input_tokens=2, output_tokens=3, total_tokens=5),
                TurnDone(
                    stop_reason="end_turn",
                    content=[TextBlock("hello")],
                    text_blocks=[TextBlock("hello")],
                    reasoning_blocks=[],
                    tool_calls=[],
                    invalid_tool_calls=[],
                    raw_stop_reason="end_turn",
                ),
            ]
        ]
    )
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        id_generator=_Ids(),
    )

    result = await kernel.run(_request())

    assert result.stop_reason == "end_turn"
    assert result.turns_count == 1
    assert result.tool_calls_count == 0
    assert result.usage.total() == 5
    assert result.messages[-1].role == "assistant"


async def test_run_kernel_stops_without_turn_when_cancelled_before_start() -> None:
    token = _CancellationToken()
    token.request_cancel()
    llm = _LLMClient(
        [
            [
                TurnDone(
                    stop_reason="end_turn",
                    content=[TextBlock("not used")],
                    text_blocks=[TextBlock("not used")],
                    reasoning_blocks=[],
                    tool_calls=[],
                    invalid_tool_calls=[],
                    raw_stop_reason="end_turn",
                )
            ]
        ]
    )
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        id_generator=_Ids(),
    )

    result = await kernel.run(_request(cancellation_token=token))

    assert result.stop_reason == "cancelled"
    assert result.turns_count == 0
    assert llm.requests == []


async def test_run_kernel_continues_after_tool_result_message() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={"path": "README.md"})
    llm = _LLMClient(
        [
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
            ],
            [
                TurnDone(
                    stop_reason="end_turn",
                    content=[TextBlock("done")],
                    text_blocks=[TextBlock("done")],
                    reasoning_blocks=[],
                    tool_calls=[],
                    invalid_tool_calls=[],
                    raw_stop_reason="end_turn",
                )
            ],
        ]
    )
    executor = _ToolExecutor()
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        id_generator=_Ids(),
    )

    result = await kernel.run(_request())

    assert result.stop_reason == "end_turn"
    assert result.turns_count == 2
    assert result.tool_calls_count == 1
    assert executor.requests[0].tool_name == "read_file"
    second_request = llm.requests[1]
    assert second_request.messages[-1].role == "tool"
    assert second_request.messages[-1].content == "result:read_file"


async def test_run_kernel_stops_when_turn_limit_reached_before_next_tool_followup() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={})
    llm = _LLMClient(
        [
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
        ]
    )
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=_ToolExecutor(),
        id_generator=_Ids(),
    )

    result = await kernel.run(_request(limits=RunLimits(max_turns=1)))

    assert result.stop_reason == "max_turns"
    assert result.turns_count == 1


async def test_run_kernel_blocks_extra_tool_calls_inside_same_turn() -> None:
    first_tool_call = ToolUseBlock(
        id="tool-1",
        name="read_file",
        input={"path": "README.md"},
    )
    second_tool_call = ToolUseBlock(
        id="tool-2",
        name="read_file",
        input={"path": "pyproject.toml"},
    )
    llm = _LLMClient(
        [
            [
                TurnDone(
                    stop_reason="tool_use",
                    content=[first_tool_call, second_tool_call],
                    text_blocks=[],
                    reasoning_blocks=[],
                    tool_calls=[first_tool_call, second_tool_call],
                    invalid_tool_calls=[],
                    raw_stop_reason="tool_use",
                )
            ]
        ]
    )
    executor = _ToolExecutor()
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        id_generator=_Ids(),
    )

    result = await kernel.run(_request(limits=RunLimits(max_tool_calls=1)))

    assert result.stop_reason == "max_tool_calls"
    assert result.turns_count == 1
    assert [request.tool_use_id for request in executor.requests] == ["tool-1"]
    assert result.tool_results[0].ok
    assert result.tool_results[1].error is not None
    assert result.tool_results[1].error["type"] == "max_tool_calls"


async def test_run_kernel_checks_timeout_before_followup_turn() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={})
    llm = _LLMClient(
        [
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
        ]
    )
    ticks = iter((100.0, 100.0, 100.2))
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=_ToolExecutor(),
        id_generator=_Ids(),
        clock=lambda: next(ticks),
    )

    result = await kernel.run(_request(limits=RunLimits(timeout_ms=100)))

    assert result.stop_reason == "max_wall_clock"
    assert result.turns_count == 1


async def test_run_kernel_blocks_on_exact_timeout_boundary() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={})
    llm = _LLMClient(
        [
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
        ]
    )
    ticks = iter((100.0, 100.0, 101.0))
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=_ToolExecutor(),
        id_generator=_Ids(),
        clock=lambda: next(ticks),
    )

    result = await kernel.run(_request(limits=RunLimits(timeout_ms=1000)))

    assert result.stop_reason == "max_wall_clock"
    assert result.turns_count == 1


async def test_run_kernel_blocks_repeated_tool_call_before_execution() -> None:
    first_tool_call = ToolUseBlock(
        id="tool-1",
        name="read_file",
        input={"path": "README.md"},
    )
    repeated_tool_call = ToolUseBlock(
        id="tool-2",
        name="read_file",
        input={"path": "README.md"},
    )
    llm = _LLMClient(
        [
            [
                TurnDone(
                    stop_reason="tool_use",
                    content=[first_tool_call],
                    text_blocks=[],
                    reasoning_blocks=[],
                    tool_calls=[first_tool_call],
                    invalid_tool_calls=[],
                    raw_stop_reason="tool_use",
                )
            ],
            [
                TurnDone(
                    stop_reason="tool_use",
                    content=[repeated_tool_call],
                    text_blocks=[],
                    reasoning_blocks=[],
                    tool_calls=[repeated_tool_call],
                    invalid_tool_calls=[],
                    raw_stop_reason="tool_use",
                )
            ],
        ]
    )
    executor = _ToolExecutor()
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=executor,
        id_generator=_Ids(),
    )

    result = await kernel.run(
        _request(limits=RunLimits(repeated_tool_call_threshold=2))
    )

    assert result.stop_reason == "repeated_tool_call"
    assert result.turns_count == 2
    assert len(executor.requests) == 1
    assert result.tool_results[-1].error is not None
    assert result.tool_results[-1].error["type"] == "repeated_tool_call"


async def test_run_kernel_applies_turn_offset_to_continuation_turn_index() -> None:
    llm = _LLMClient(
        [
            [
                TurnDone(
                    stop_reason="end_turn",
                    content=[TextBlock("done")],
                    text_blocks=[TextBlock("done")],
                    reasoning_blocks=[],
                    tool_calls=[],
                    invalid_tool_calls=[],
                    raw_stop_reason="end_turn",
                )
            ]
        ]
    )
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        id_generator=_Ids(),
    )

    await kernel.run(_request(turn_offset=4))

    assert llm.requests[0].turn_index == 5


def test_run_request_rejects_negative_turn_offset() -> None:
    try:
        _request(turn_offset=-1)
    except ValueError as exc:
        assert "turn_offset" in str(exc)
    else:
        raise AssertionError("Expected negative turn_offset to fail")


async def test_run_kernel_respects_pause_tool_policy() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="ask_user", input={})
    llm = _LLMClient(
        [
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
        ]
    )
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(_InMemoryEventLog(), run_id="run-1"),
        tool_executor=_ToolExecutor(),
        tool_policy=CoreToolPolicy(
            pause_tool_names=frozenset({"ask_user"}),
            pause_stop_reason="ask_user",
        ),
        id_generator=_Ids(),
    )

    result = await kernel.run(
        _request(
            tools=(
                ToolDefinition(
                    name="ask_user",
                    description="Ask user",
                    input_schema={"type": "object"},
                ),
            )
        )
    )

    assert result.stop_reason == "ask_user"
    assert result.turns_count == 1


def test_build_messages_after_turn_pairs_tool_results() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={})
    messages = build_messages_after_turn(
        turn_id="turn-1",
        assistant_message_id="msg-assistant",
        content=(tool_call,),
        tool_results=(ToolExecutionResult(ok=True, content="ok"),),
        id_generator=_Ids(),
    )

    assert messages[0].role == "assistant"
    assert messages[0].tool_calls[0].tool_name == "read_file"
    assert messages[1].role == "tool"
    assert messages[1].tool_results[0].tool_use_id == "tool-1"


def test_build_messages_after_turn_rejects_unpaired_tool_results() -> None:
    tool_call = ToolUseBlock(id="tool-1", name="read_file", input={})

    try:
        build_messages_after_turn(
            turn_id="turn-1",
            assistant_message_id="msg-assistant",
            content=(tool_call,),
            tool_results=(),
            id_generator=_Ids(),
        )
    except ValueError as exc:
        assert "one-to-one" in str(exc)
    else:
        raise AssertionError("Expected unpaired tool results to fail")
