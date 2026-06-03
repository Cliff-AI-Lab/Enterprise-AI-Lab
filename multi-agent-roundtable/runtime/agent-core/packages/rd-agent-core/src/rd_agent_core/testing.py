"""Reusable test harness for host integrations.

The harness intentionally lives in ``rd_agent_core.testing`` instead of the
main runtime namespace. It gives product hosts a small, deterministic way to
verify their agent wiring without importing private test fixtures.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterable, Awaitable, Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from rd_agent_contracts import (
    ActionId,
    AgentEvent,
    AgentKind,
    EventDraft,
    Message,
    MessageId,
    RunBudget,
    RunCompletion,
    RunFailure,
    RunId,
    RunRecord,
    RunResultMetadata,
    RunScope,
    RunStatus,
    SessionId,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolUseId,
    TurnId,
)
from rd_llm_adapter.events import StandardEvent

from .events import CoreEventWriter
from .policies import RunLimits
from .run import RunKernel, RunKernelResult, RunRequest
from .turn import LLMClientPort, ToolExecutorLike, TurnRequest


class DeterministicIdGenerator:
    """Stable ID generator for harness runs and snapshot-friendly tests."""

    def __init__(self) -> None:
        self._run = 0
        self._turn = 0
        self._message = 0
        self._action = 0
        self._tool = 0
        self._session = 0

    def run_id(self) -> RunId:
        self._run += 1
        return RunId(f"run-{self._run}")

    def turn_id(self) -> TurnId:
        self._turn += 1
        return TurnId(f"turn-{self._turn}")

    def message_id(self) -> MessageId:
        self._message += 1
        return MessageId(f"msg-{self._message}")

    def action_id(self) -> ActionId:
        self._action += 1
        return ActionId(f"act-{self._action}")

    def tool_use_id(self) -> ToolUseId:
        self._tool += 1
        return ToolUseId(f"tool-{self._tool}")

    def session_id(self) -> SessionId:
        self._session += 1
        return SessionId(f"session-{self._session}")


class InMemoryEventLog:
    """Append-only event log with per-run sequences and idempotency."""

    def __init__(self, *, timestamp_ms: int = 1_710_000_000_000) -> None:
        self.timestamp_ms = timestamp_ms
        self.events_by_run: dict[str, list[AgentEvent]] = {}
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

        events = self.events_by_run.setdefault(run_id, [])
        event = draft.to_event(
            run_id=run_id,
            seq=len(events) + 1,
            timestamp_ms=self.timestamp_ms + len(events),
        )
        events.append(event)
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
            for event in self.events_by_run.get(run_id, ())
            if event.seq > from_seq
        ]
        return events[:limit] if limit is not None else events


class InMemoryRunPersistence:
    """In-memory ``RunPersistencePort`` implementation for contract tests."""

    def __init__(self, *, timestamp_ms: int = 1_710_000_000_000) -> None:
        self.timestamp_ms = timestamp_ms
        self.records: dict[str, RunRecord] = {}
        self._next_index = 1

    def create_root_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        return self._create_run(
            scope=scope,
            budget=budget,
            max_continuations=max_continuations,
            continuation_index=0,
            engine_state_json=None,
            run_id=run_id,
        )

    def create_subagent_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        return self._create_run(
            scope=scope,
            budget=budget,
            max_continuations=max_continuations,
            continuation_index=0,
            engine_state_json=None,
            run_id=run_id,
        )

    def create_continuation_run(
        self,
        *,
        previous_run_id: str,
        engine_state_json: str,
        run_id: str | None = None,
    ) -> RunRecord | None:
        previous = self.records.get(previous_run_id)
        if previous is None:
            return None
        next_continuation = previous.continuation_index + 1
        if next_continuation > previous.max_continuations:
            return None

        return self._create_run(
            scope=replace(previous.scope, parent_run_id=previous.run_id),
            budget=previous.budget,
            max_continuations=previous.max_continuations,
            continuation_index=next_continuation,
            engine_state_json=engine_state_json,
            run_id=run_id,
        )

    def mark_running(
        self,
        run_id: str,
        *,
        started_at_ms: int | None = None,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.RUNNING,
            started_at_ms=started_at_ms,
        )

    def mark_completed(
        self,
        run_id: str,
        *,
        completion: RunCompletion,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.COMPLETED,
            stop_reason=completion.stop_reason,
            result_metadata=completion.metadata,
            engine_state_json=completion.engine_state_json,
            completed_at_ms=completion.completed_at_ms,
        )

    def mark_failed(
        self,
        run_id: str,
        *,
        failure: RunFailure,
    ) -> RunRecord | None:
        return self._update(
            run_id,
            status=RunStatus.FAILED,
            error_message=failure.error_message,
            completed_at_ms=failure.completed_at_ms,
        )

    def mark_resumed(self, run_id: str) -> RunRecord | None:
        return self._update(run_id, status=RunStatus.RESUMED)

    def claim_latest_waiting_orchestrator_run(
        self,
        *,
        project_id: str,
    ) -> RunRecord | None:
        candidates = [
            record
            for record in self.records.values()
            if record.scope.project_id == project_id
            and record.scope.agent_kind == AgentKind.ORCHESTRATOR
            and record.status == RunStatus.WAITING_USER
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda record: record.created_at_ms or 0)
        return self._update(latest.run_id, status=RunStatus.RESUMING)

    def load_run(self, run_id: str) -> RunRecord | None:
        return self.records.get(run_id)

    def load_run_with_parent(
        self,
        run_id: str,
    ) -> tuple[RunRecord, RunRecord | None] | None:
        record = self.records.get(run_id)
        if record is None:
            return None
        parent = (
            self.records.get(record.scope.parent_run_id)
            if record.scope.parent_run_id
            else None
        )
        return record, parent

    def _create_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget | None,
        max_continuations: int,
        continuation_index: int,
        engine_state_json: str | None,
        run_id: str | None,
    ) -> RunRecord:
        resolved_run_id = run_id
        while resolved_run_id is None:
            candidate = f"run-{self._next_index}"
            if candidate not in self.records:
                resolved_run_id = candidate
            else:
                self._next_index += 1
        if resolved_run_id in self.records:
            raise ValueError(f"run_id already exists: {resolved_run_id}")
        record = RunRecord(
            run_id=resolved_run_id,
            scope=scope,
            status=RunStatus.PENDING,
            run_index=self._next_index,
            continuation_index=continuation_index,
            max_continuations=max_continuations,
            budget=budget,
            engine_state_json=engine_state_json,
            created_at_ms=self.timestamp_ms + self._next_index,
        )
        self._next_index += 1
        self.records[record.run_id] = record
        return record

    def _update(self, run_id: str, **changes: Any) -> RunRecord | None:
        record = self.records.get(run_id)
        if record is None:
            return None
        updated = replace(record, **changes)
        self.records[run_id] = updated
        return updated


ScriptedTurn = (
    Sequence[StandardEvent]
    | Callable[[TurnRequest], Iterable[StandardEvent] | AsyncIterable[StandardEvent]]
)


class ScriptedLLMClient:
    """LLM client that emits deterministic per-turn event scripts."""

    def __init__(self, turns: Sequence[ScriptedTurn]) -> None:
        self.turns = tuple(turns)
        self.requests: list[TurnRequest] = []

    async def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]:
        turn_index = len(self.requests)
        self.requests.append(request)
        if turn_index >= len(self.turns):
            raise RuntimeError(f"no scripted LLM turn at index {turn_index}")

        events = self.turns[turn_index]
        stream = events(request) if callable(events) else events
        if hasattr(stream, "__aiter__"):
            async for event in stream:  # type: ignore[union-attr]
                yield event
            return
        for event in stream:
            yield event


ToolHandlerResult = ToolExecutionResult | str | Mapping[str, Any]
ToolHandler = Callable[
    [ToolExecutionRequest],
    ToolHandlerResult | Awaitable[ToolHandlerResult],
]


class FunctionToolExecutor:
    """Tool executor backed by simple Python callables."""

    def __init__(self, handlers: Mapping[str, ToolHandler]) -> None:
        self.handlers = dict(handlers)
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        handler = self.handlers.get(request.tool_name)
        if handler is None:
            return ToolExecutionResult(
                ok=False,
                content="",
                error={
                    "type": "tool_handler_missing",
                    "message": f"No handler registered for tool: {request.tool_name}",
                },
            )

        raw = handler(request)
        value = await raw if inspect.isawaitable(raw) else raw
        if isinstance(value, ToolExecutionResult):
            return value
        if isinstance(value, str):
            return ToolExecutionResult(ok=True, content=value)
        return ToolExecutionResult(
            ok=True,
            content=json.dumps(value, ensure_ascii=False, sort_keys=True),
        )


@dataclass(frozen=True)
class HarnessRunResult:
    run: RunRecord
    completed: RunRecord
    kernel_result: RunKernelResult
    events: tuple[AgentEvent, ...]


class AgentCoreHarness:
    """End-to-end local host harness for ``RunKernel`` contract tests."""

    def __init__(
        self,
        *,
        llm_client: LLMClientPort,
        tool_executor: ToolExecutorLike | None = None,
        event_log: InMemoryEventLog | None = None,
        persistence: InMemoryRunPersistence | None = None,
        id_generator: DeterministicIdGenerator | None = None,
        timestamp_ms: int = 1_710_000_000_000,
    ) -> None:
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.event_log = event_log or InMemoryEventLog(timestamp_ms=timestamp_ms)
        self.persistence = persistence or InMemoryRunPersistence(
            timestamp_ms=timestamp_ms
        )
        self.id_generator = id_generator or DeterministicIdGenerator()
        self.timestamp_ms = timestamp_ms

    async def run(
        self,
        *,
        run_id: str | None = None,
        messages: Sequence[Message] = (),
        tools: Sequence[ToolDefinition] = (),
        tool_context: ToolExecutionContext | None = None,
        scope: RunScope | None = None,
        budget: RunBudget | None = None,
        limits: RunLimits | None = None,
        model: str | None = None,
        system_prompt: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        max_continuations: int = 0,
    ) -> HarnessRunResult:
        resolved_scope = scope or RunScope(
            user_request_id="request-harness",
            project_id="project-harness",
            session_id="session-harness",
        )
        resolved_budget = budget or RunBudget(
            max_turns=3,
            max_tool_calls=3,
            max_wall_clock_s=30,
            total_timeout_s=60,
        )
        resolved_limits = limits or RunLimits(
            max_turns=resolved_budget.max_turns,
            max_tool_calls=resolved_budget.max_tool_calls,
            timeout_ms=resolved_budget.max_wall_clock_s * 1000,
        )
        resolved_context = tool_context or ToolExecutionContext(
            project_id=resolved_scope.project_id,
            metadata={"session_id": resolved_scope.session_id},
        )

        resolved_run_id = run_id or str(self.id_generator.run_id())
        run = self.persistence.create_root_run(
            scope=resolved_scope,
            budget=resolved_budget,
            max_continuations=max_continuations,
            run_id=resolved_run_id,
        )
        self.persistence.mark_running(run.run_id, started_at_ms=self.timestamp_ms + 1)

        kernel = RunKernel(
            llm_client=self.llm_client,
            event_writer=CoreEventWriter(self.event_log, run_id=run.run_id),
            tool_executor=self.tool_executor,
            id_generator=self.id_generator,
        )
        kernel_result = await kernel.run(
            RunRequest(
                run_id=run.run_id,
                messages=tuple(messages),
                tool_context=resolved_context,
                tools=tuple(tools),
                model=model,
                system_prompt=system_prompt,
                limits=resolved_limits,
                metadata=dict(metadata or {}),
            )
        )
        completed = self.persistence.mark_completed(
            run.run_id,
            completion=RunCompletion(
                stop_reason=kernel_result.stop_reason,
                metadata=RunResultMetadata(
                    usage=kernel_result.usage,
                    turns_count=kernel_result.turns_count,
                    tool_calls_count=kernel_result.tool_calls_count,
                    extra={"event_count": len(kernel_result.events)},
                ),
                completed_at_ms=self.timestamp_ms + 2,
            ),
        )
        if completed is None:
            raise RuntimeError(f"harness run disappeared: {run.run_id}")

        return HarnessRunResult(
            run=run,
            completed=completed,
            kernel_result=kernel_result,
            events=tuple(self.event_log.stream_events(run.run_id)),
        )
