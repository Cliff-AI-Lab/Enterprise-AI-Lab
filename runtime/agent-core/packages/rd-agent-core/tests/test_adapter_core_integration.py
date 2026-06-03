from __future__ import annotations

from collections.abc import AsyncIterable, Iterable
from typing import Any

from rd_agent_contracts import (
    AgentEvent,
    EventDraft,
    MessageId,
    RunId,
    SessionId,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolUseId,
    TurnId,
)
from rd_agent_core import CoreEventType, CoreEventWriter, RunKernel, RunRequest, TurnRequest
from rd_llm_adapter import OpenAICompatAdapter
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

    def action_id(self) -> str:
        return "act-fixed"

    def tool_use_id(self) -> ToolUseId:
        return ToolUseId("tool-fixed")

    def session_id(self) -> SessionId:
        return SessionId("session-fixed")


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
        events = [
            event
            for event in self.events
            if event.run_id == run_id and event.seq > from_seq
        ]
        if limit is not None:
            return events[:limit]
        return events


class _AdapterBackedLLM:
    def __init__(self, raw_turns: list[list[dict[str, Any]]]) -> None:
        self.raw_turns = raw_turns
        self.requests: list[TurnRequest] = []

    async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
        self.requests.append(request)
        session = OpenAICompatAdapter().create_parser_session()
        raw_chunks = self.raw_turns[len(self.requests) - 1]
        for chunk in raw_chunks:
            for event in session.feed(chunk):
                yield event
        for event in session.finalize():
            yield event


class _ToolExecutor:
    def __init__(self) -> None:
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        return ToolExecutionResult(
            ok=True,
            content=f"file:{request.tool_input['path']}",
            duration_ms=4,
        )


async def test_openai_adapter_stream_drives_core_run_loop() -> None:
    llm = _AdapterBackedLLM(
        [
            [
                {
                    "choices": [
                        {
                            "delta": {
                                "tool_calls": [
                                    {
                                        "index": 0,
                                        "id": "call-1",
                                        "function": {
                                            "name": "read_file",
                                            "arguments": '{"path":"README.md"}',
                                        },
                                    }
                                ]
                            },
                            "finish_reason": "tool_calls",
                        }
                    ]
                },
                {
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 4,
                        "prompt_tokens_details": {
                            "cached_tokens": 2,
                            "cache_creation_input_tokens": 3,
                        },
                    },
                },
            ],
            [
                {
                    "choices": [
                        {
                            "delta": {"content": "read complete"},
                            "finish_reason": "stop",
                        }
                    ]
                },
                {"choices": [], "usage": {"prompt_tokens": 20, "completion_tokens": 5}},
            ],
        ]
    )
    event_log = _InMemoryEventLog()
    executor = _ToolExecutor()
    kernel = RunKernel(
        llm_client=llm,
        event_writer=CoreEventWriter(event_log, run_id="run-1"),
        tool_executor=executor,
        id_generator=_Ids(),
    )

    result = await kernel.run(
        RunRequest(
            run_id="run-1",
            messages=(),
            tool_context=ToolExecutionContext(project_id="project-1"),
            tools=(
                ToolDefinition(
                    name="read_file",
                    description="Read a file from the workspace",
                    input_schema={"type": "object", "properties": {"path": {"type": "string"}}},
                ),
            ),
            model="openai-compatible-test",
        )
    )

    assert result.stop_reason == "stop"
    assert result.turns_count == 2
    assert result.tool_calls_count == 1
    assert result.usage.input_tokens == 32
    assert result.usage.output_tokens == 9
    assert result.usage.cache_read_input_tokens == 2
    assert result.usage.cache_creation_input_tokens == 3
    assert executor.requests[0].tool_name == "read_file"
    assert llm.requests[1].messages[-1].role == "tool"
    assert llm.requests[1].messages[-1].content == "file:README.md"

    event_types = [event.event_type for event in event_log.events]
    assert CoreEventType.TOOL_COMPLETED in event_types
    assert event_types.count(CoreEventType.TURN_COMPLETED) == 2
