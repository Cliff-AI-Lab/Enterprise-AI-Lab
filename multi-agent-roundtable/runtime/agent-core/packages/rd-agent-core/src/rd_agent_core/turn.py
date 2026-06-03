"""Turn-level runtime kernel.

The kernel consumes provider-normalized ``rd-llm-adapter`` events, writes
canonical ``AgentEvent`` records, and executes completed tool calls through
injected contracts. It intentionally has no database, SaaS, frontend, or
business-agent dependencies.
"""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass, replace
from typing import Any, Protocol

from rd_agent_contracts import (
    AgentEvent,
    CancellationToken,
    InvalidToolCall,
    Message,
    StandardContentBlock,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolExecutorPort,
    ToolObservabilityPort,
    ToolObservabilityRecord,
    ToolUseBlock,
    Usage,
)
from rd_llm_adapter.events import (
    ReasoningDelta,
    StandardEvent,
    TextDelta,
    ToolCallArgsDelta,
    ToolCallEnd,
    ToolCallIdDelta,
    ToolCallNameDelta,
    ToolCallStart,
    TurnDone,
    UsageUpdate,
)

from .errors import CoreErrorType, core_error
from .events import CoreEventType, CoreEventWriter


@dataclass(frozen=True)
class TurnRequest:
    run_id: str
    turn_id: str
    messages: Sequence[Message]
    tool_context: ToolExecutionContext
    model: str | None = None
    system_prompt: str | None = None
    tools: Sequence[ToolDefinition] = ()
    turn_index: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    cancellation_token: CancellationToken | None = None


@dataclass(frozen=True)
class ToolSafetyPolicy:
    allowed_tool_names: frozenset[str] | None = None
    blocked_tool_names: frozenset[str] = field(default_factory=frozenset)
    require_confirmation_for_mutating_tools: bool = False
    confirmed_tool_use_ids: frozenset[str] = field(default_factory=frozenset)

    def evaluate(
        self,
        tool_call: ToolUseBlock,
        declared_tools: Sequence[ToolDefinition],
    ) -> ToolExecutionResult | None:
        details = {"tool_name": tool_call.name, "tool_use_id": tool_call.id}
        if tool_call.name in self.blocked_tool_names:
            return _tool_policy_denial(
                "tool_blocked",
                "Tool call blocked by tool safety policy.",
                details,
            )
        if (
            self.allowed_tool_names is not None
            and tool_call.name not in self.allowed_tool_names
        ):
            return _tool_policy_denial(
                "tool_not_allowed",
                "Tool call is not in the safety policy allowlist.",
                details,
            )

        declared_tool = next(
            (tool for tool in declared_tools if tool.name == tool_call.name),
            None,
        )
        if (
            declared_tool is not None
            and declared_tool.mutates_workspace
            and self.require_confirmation_for_mutating_tools
            and tool_call.id not in self.confirmed_tool_use_ids
        ):
            return _tool_policy_denial(
                "tool_confirmation_required",
                "Mutating tool call requires host confirmation.",
                details,
            )
        return None


@dataclass(frozen=True)
class CoreToolPolicy:
    pause_tool_names: frozenset[str] = field(default_factory=frozenset)
    pause_stop_reason: str = "pause_requested"
    safety_policy: ToolSafetyPolicy = field(default_factory=ToolSafetyPolicy)

    def is_pause_tool(self, tool_name: str) -> bool:
        return tool_name in self.pause_tool_names


@dataclass(frozen=True)
class TurnKernelResult:
    stop_reason: str
    raw_stop_reason: str
    content: tuple[StandardContentBlock, ...]
    usage: Usage
    tool_results: tuple[ToolExecutionResult, ...]
    invalid_tool_calls: tuple[InvalidToolCall, ...]
    events: tuple[AgentEvent, ...]
    pause_requested: bool = False
    provider_state: Any | None = None

    @property
    def tool_calls_executed(self) -> int:
        return len(self.tool_results)


class LLMClientPort(Protocol):
    def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]: ...


class AsyncToolExecutorPort(Protocol):
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult: ...


ToolExecutorLike = ToolExecutorPort | AsyncToolExecutorPort


class TurnKernel:
    def __init__(
        self,
        *,
        llm_client: LLMClientPort,
        event_writer: CoreEventWriter,
        tool_executor: ToolExecutorLike | None = None,
        tool_observability: ToolObservabilityPort | None = None,
        tool_policy: CoreToolPolicy | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._event_writer = event_writer
        self._tool_executor = tool_executor
        self._tool_observability = tool_observability
        self._tool_policy = tool_policy or CoreToolPolicy()

    async def run_turn(self, request: TurnRequest) -> TurnKernelResult:
        if request.run_id != self._event_writer.run_id:
            raise ValueError("TurnRequest.run_id must match CoreEventWriter.run_id")

        writer = self._event_writer.with_turn(request.turn_id)
        events: list[AgentEvent] = [
            writer.append(
                CoreEventType.TURN_STARTED,
                {
                    "model": request.model,
                    "turn_index": request.turn_index,
                    "metadata": dict(request.metadata),
                },
                idempotency_key=f"{request.turn_id}:turn_started",
            )
        ]
        turn_done: TurnDone | None = None
        last_usage_update: UsageUpdate | None = None
        usage_update_index = 0
        cancelled = _is_cancelled(request.cancellation_token)

        if not cancelled:
            async for event in self._llm_client.stream_turn(request):
                if isinstance(event, UsageUpdate):
                    usage_update_index += 1
                    last_usage_update = event
                    emitted = self._emit_standard_event(
                        writer,
                        event,
                        usage_update_index=usage_update_index,
                    )
                elif isinstance(event, TurnDone):
                    turn_done = event
                    emitted = self._emit_standard_event(writer, event)
                else:
                    emitted = self._emit_standard_event(writer, event)
                if emitted is not None:
                    events.append(emitted)
                if _is_cancelled(request.cancellation_token):
                    cancelled = True
                    break

        if cancelled:
            usage = _usage_from_update(last_usage_update)
            events.append(
                writer.append(
                    CoreEventType.TURN_COMPLETED,
                    {
                        "stop_reason": CoreErrorType.CANCELLED.value,
                        "raw_stop_reason": CoreErrorType.CANCELLED.value,
                        "tool_calls_executed": 0,
                        "invalid_tool_calls": 0,
                        "pause_requested": False,
                        "terminal_text": "",
                        "terminal_reasoning": "",
                        "usage": asdict(usage),
                    },
                    idempotency_key=f"{request.turn_id}:turn_completed",
                )
            )
            return TurnKernelResult(
                stop_reason=CoreErrorType.CANCELLED.value,
                raw_stop_reason=CoreErrorType.CANCELLED.value,
                content=(),
                usage=usage,
                tool_results=(),
                invalid_tool_calls=(),
                events=tuple(events),
            )

        if turn_done is None:
            raise RuntimeError("LLMClientPort.stream_turn completed without TurnDone")

        invalid_tool_calls = tuple(
            block for block in turn_done.content if isinstance(block, InvalidToolCall)
        )
        for invalid in invalid_tool_calls:
            events.append(
                writer.append(
                    CoreEventType.TOOL_CALL_INVALID,
                    _dataclass_payload(invalid),
                    idempotency_key=f"{request.turn_id}:invalid_tool:{invalid.id}",
                )
            )

        tool_results: list[ToolExecutionResult] = []
        pause_requested = False
        for tool_call in (block for block in turn_done.content if isinstance(block, ToolUseBlock)):
            if _is_cancelled(request.cancellation_token):
                cancelled = True
                result, result_events = self._skip_tool_after_cancellation(
                    writer,
                    request,
                    tool_call,
                )
            elif pause_requested:
                result, result_events = self._skip_tool_after_pause(writer, request, tool_call)
            else:
                result, result_events = await self._execute_tool(writer, request, tool_call)
            tool_results.append(result)
            events.extend(result_events)
            if result.ok and self._tool_policy.is_pause_tool(tool_call.name):
                pause_requested = True
                events.append(
                    writer.append(
                        CoreEventType.TURN_PAUSED,
                        {
                            "tool_name": tool_call.name,
                            "tool_use_id": tool_call.id,
                            "stop_reason": self._tool_policy.pause_stop_reason,
                        },
                        idempotency_key=f"{request.turn_id}:paused:{tool_call.id}",
                    )
                )

        usage = _usage_from_update(turn_done.usage or last_usage_update)
        final_stop_reason = CoreErrorType.CANCELLED.value if cancelled else (
            self._tool_policy.pause_stop_reason if pause_requested else turn_done.stop_reason
        )
        events.append(
            writer.append(
                CoreEventType.TURN_COMPLETED,
                {
                    "stop_reason": final_stop_reason,
                    "raw_stop_reason": turn_done.raw_stop_reason,
                    "tool_calls_executed": len(tool_results),
                    "invalid_tool_calls": len(invalid_tool_calls),
                    "pause_requested": pause_requested,
                    "terminal_text": _joined_content_text(turn_done.content, "text"),
                    "terminal_reasoning": _joined_content_text(
                        turn_done.content,
                        "reasoning",
                    ),
                    "usage": asdict(usage),
                },
                idempotency_key=f"{request.turn_id}:turn_completed",
            )
        )

        return TurnKernelResult(
            stop_reason=final_stop_reason,
            raw_stop_reason=turn_done.raw_stop_reason,
            content=tuple(turn_done.content),
            usage=usage,
            tool_results=tuple(tool_results),
            invalid_tool_calls=invalid_tool_calls,
            events=tuple(events),
            pause_requested=pause_requested,
            provider_state=turn_done.provider_state,
        )

    def _skip_tool_after_pause(
        self,
        writer: CoreEventWriter,
        request: TurnRequest,
        tool_call: ToolUseBlock,
    ) -> tuple[ToolExecutionResult, list[AgentEvent]]:
        message = "Execution paused before this tool call because a pause tool already ran."
        result = ToolExecutionResult(
            ok=False,
            content=message,
            error={
                "type": "tool_skipped_after_pause",
                "message": message,
                "category": "tool_policy",
                "details": {
                    "tool_name": tool_call.name,
                    "tool_use_id": tool_call.id,
                },
            },
        )
        return result, [
            writer.append(
                CoreEventType.TOOL_STARTED,
                {"tool_name": tool_call.name, "tool_use_id": tool_call.id},
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:started",
            ),
            writer.append(
                CoreEventType.TOOL_FAILED,
                {
                    "tool_name": tool_call.name,
                    "tool_use_id": tool_call.id,
                    "result": _dataclass_payload(result),
                },
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:completed",
            ),
        ]

    def _skip_tool_after_cancellation(
        self,
        writer: CoreEventWriter,
        request: TurnRequest,
        tool_call: ToolUseBlock,
    ) -> tuple[ToolExecutionResult, list[AgentEvent]]:
        message = "Execution cancelled before this tool call ran."
        result = ToolExecutionResult(
            ok=False,
            content=message,
            error=core_error(
                CoreErrorType.CANCELLED.value,
                message,
                details={
                    "tool_name": tool_call.name,
                    "tool_use_id": tool_call.id,
                },
            ),
        )
        return result, [
            writer.append(
                CoreEventType.TOOL_STARTED,
                {"tool_name": tool_call.name, "tool_use_id": tool_call.id},
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:started",
            ),
            writer.append(
                CoreEventType.TOOL_FAILED,
                {
                    "tool_name": tool_call.name,
                    "tool_use_id": tool_call.id,
                    "result": _dataclass_payload(result),
                },
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:completed",
            ),
        ]

    def _emit_standard_event(
        self,
        writer: CoreEventWriter,
        event: StandardEvent,
        *,
        usage_update_index: int | None = None,
    ) -> AgentEvent | None:
        if isinstance(event, TextDelta):
            return writer.append(
                CoreEventType.TEXT_DELTA,
                {"text": event.text, "block_index": event.block_index},
            )
        if isinstance(event, ReasoningDelta):
            return writer.append(
                CoreEventType.REASONING_DELTA,
                {
                    "text": event.text,
                    "block_index": event.block_index,
                    "provider_data": event.provider_data,
                },
            )
        if isinstance(event, ToolCallStart):
            return writer.append(
                CoreEventType.TOOL_CALL_STARTED,
                _dataclass_payload(event),
            )
        if isinstance(event, ToolCallIdDelta | ToolCallNameDelta | ToolCallArgsDelta):
            return writer.append(
                CoreEventType.TOOL_CALL_DELTA,
                _dataclass_payload(event),
            )
        if isinstance(event, ToolCallEnd):
            return writer.append(
                CoreEventType.TOOL_CALL_COMPLETED,
                _dataclass_payload(event),
            )
        if isinstance(event, UsageUpdate):
            payload = event.to_dict()
            if usage_update_index is not None:
                payload["usage_sequence"] = usage_update_index
            return writer.append(
                CoreEventType.USAGE_UPDATE,
                payload,
                idempotency_key=(
                    f"{writer.turn_id}:usage:{usage_update_index}"
                    if usage_update_index is not None
                    else None
                ),
            )
        return None

    async def _execute_tool(
        self,
        writer: CoreEventWriter,
        request: TurnRequest,
        tool_call: ToolUseBlock,
    ) -> tuple[ToolExecutionResult, list[AgentEvent]]:
        events = [
            writer.append(
                CoreEventType.TOOL_STARTED,
                {"tool_name": tool_call.name, "tool_use_id": tool_call.id},
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:started",
            )
        ]

        declared_tool_names = {tool.name for tool in request.tools}
        if declared_tool_names and tool_call.name not in declared_tool_names:
            result = ToolExecutionResult(
                ok=False,
                content="",
                error={
                    "type": "tool_not_declared",
                    "message": f"Tool is not declared for this turn: {tool_call.name}",
                    "category": "tool_unavailable",
                },
            )
        elif (
            safety_result := self._tool_policy.safety_policy.evaluate(
                tool_call,
                request.tools,
            )
        ) is not None:
            result = safety_result
        elif self._tool_executor is None:
            result = ToolExecutionResult(
                ok=False,
                content="",
                error={
                    "type": "tool_executor_missing",
                    "message": "No ToolExecutorPort was provided for tool execution.",
                    "category": "tool_unavailable",
                },
            )
        else:
            try:
                tool_context = replace(
                    request.tool_context,
                    metadata={
                        **dict(request.tool_context.metadata),
                        "core_turn_id": request.turn_id,
                    },
                )
                raw_result = self._tool_executor.execute_tool(
                    ToolExecutionRequest(
                        tool_name=tool_call.name,
                        tool_input=dict(tool_call.input),
                        context=tool_context,
                        tool_use_id=tool_call.id,
                        turn=request.turn_index,
                    )
                )
                result = await raw_result if inspect.isawaitable(raw_result) else raw_result
            except Exception as exc:  # noqa: BLE001 - tool boundary must fail closed.
                result = ToolExecutionResult(
                    ok=False,
                    content="",
                    error=core_error(
                        exc.__class__.__name__,
                        str(exc),
                        category="tool_error",
                    ),
                )

        completed_type = CoreEventType.TOOL_COMPLETED if result.ok else CoreEventType.TOOL_FAILED
        events.append(
            writer.append(
                completed_type,
                {
                    "tool_name": tool_call.name,
                    "tool_use_id": tool_call.id,
                    "result": _dataclass_payload(result),
                },
                idempotency_key=f"{request.turn_id}:tool:{tool_call.id}:completed",
            )
        )
        self._record_tool_observability(request, tool_call, result)
        return result, events

    def _record_tool_observability(
        self,
        request: TurnRequest,
        tool_call: ToolUseBlock,
        result: ToolExecutionResult,
    ) -> None:
        if self._tool_observability is None:
            return
        self._tool_observability.record_tool_calls(
            [
                ToolObservabilityRecord(
                    project_id=request.tool_context.project_id,
                    session_id=request.tool_context.session_id,
                    tool_name=tool_call.name,
                    tool_input=tool_call.input,
                    tool_output=result.content,
                    ok=result.ok,
                    correlation_id=request.tool_context.correlation_id,
                    error=result.error,
                    duration_ms=result.duration_ms,
                    tool_use_id=tool_call.id,
                    turn=request.turn_index,
                )
            ]
        )


def _usage_from_update(update: UsageUpdate | None) -> Usage:
    if update is None:
        return Usage()
    return Usage(
        input_tokens=update.input_tokens,
        output_tokens=update.output_tokens,
        cache_creation_input_tokens=update.cache_creation_input_tokens,
        cache_read_input_tokens=update.cache_read_input_tokens,
    )


def _dataclass_payload(value: Any) -> dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    return dict(value)


def _tool_policy_denial(
    error_type: str,
    message: str,
    details: dict[str, Any],
) -> ToolExecutionResult:
    return ToolExecutionResult(
        ok=False,
        content="",
        error=core_error(error_type, message, details=details),
    )


def _joined_content_text(content: Sequence[StandardContentBlock], block_type: str) -> str:
    return "".join(
        str(getattr(block, "text", "") or "")
        for block in content
        if getattr(block, "type", "") == block_type
    )


def _is_cancelled(token: CancellationToken | None) -> bool:
    return token is not None and token.is_cancelled()
