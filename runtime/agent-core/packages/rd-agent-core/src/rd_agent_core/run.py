"""Multi-turn host-neutral run kernel."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from rd_agent_contracts import (
    AgentEvent,
    CancellationToken,
    IdGenerator,
    Message,
    StandardContentBlock,
    ToolCall,
    ToolCallStatus,
    ToolDefinition,
    ToolExecutionContext,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolObservabilityPort,
    ToolResult,
    ToolUseBlock,
    Usage,
    UuidIdGenerator,
)

from .errors import CoreErrorType, core_error
from .events import CoreEventWriter
from .policies import (
    RunLimits,
    RunLimitState,
    ToolCallSignature,
    evaluate_run_limits,
    tool_call_signature,
)
from .turn import (
    CoreToolPolicy,
    LLMClientPort,
    ToolExecutorLike,
    TurnKernel,
    TurnKernelResult,
    TurnRequest,
)


@dataclass(frozen=True)
class RunRequest:
    """Input for a bounded run kernel invocation.

    ``turn_offset`` is the number of turns already committed before this
    invocation. Hosts must set it when creating a continuation run so emitted
    ``turn_index`` values remain monotonic across run boundaries.
    """

    run_id: str
    messages: tuple[Message, ...]
    tool_context: ToolExecutionContext
    tools: tuple[ToolDefinition, ...] = ()
    model: str | None = None
    system_prompt: str | None = None
    limits: RunLimits = field(default_factory=RunLimits)
    metadata: dict[str, Any] = field(default_factory=dict)
    turn_offset: int = 0
    cancellation_token: CancellationToken | None = None

    def __post_init__(self) -> None:
        if self.turn_offset < 0:
            raise ValueError("turn_offset must be >= 0")


@dataclass(frozen=True)
class RunKernelResult:
    stop_reason: str
    messages: tuple[Message, ...]
    turns_count: int
    tool_calls_count: int
    usage: Usage
    turn_results: tuple[TurnKernelResult, ...]
    events: tuple[AgentEvent, ...]
    tool_results: tuple[ToolExecutionResult, ...]


class RunKernel:
    def __init__(
        self,
        *,
        llm_client: LLMClientPort,
        event_writer: CoreEventWriter,
        tool_executor: ToolExecutorLike | None = None,
        tool_observability: ToolObservabilityPort | None = None,
        tool_policy: CoreToolPolicy | None = None,
        id_generator: IdGenerator | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._llm_client = llm_client
        self._event_writer = event_writer
        self._tool_executor = tool_executor
        self._tool_observability = tool_observability
        self._tool_policy = tool_policy or CoreToolPolicy()
        self._id_generator = id_generator or UuidIdGenerator()
        self._clock = clock or time.monotonic

    async def run(self, request: RunRequest) -> RunKernelResult:
        """Run turns until the model stops, pauses, or a run limit is reached.

        Repeated tool-call tracking intentionally spans all turns in this run
        invocation. That catches retry loops where the model keeps issuing the
        same tool call after seeing the previous tool result.
        """

        if request.run_id != self._event_writer.run_id:
            raise ValueError("RunRequest.run_id must match CoreEventWriter.run_id")

        started_at = self._clock()
        messages = list(request.messages)
        turn_results: list[TurnKernelResult] = []
        all_events: list[AgentEvent] = []
        all_tool_results: list[ToolExecutionResult] = []
        usage = Usage()
        tool_calls_count = 0
        stop_reason = "end_turn"
        tool_signatures: list[ToolCallSignature] = []

        while True:
            if _is_cancelled(request.cancellation_token):
                stop_reason = CoreErrorType.CANCELLED.value
                break

            state = RunLimitState(
                turns_used=len(turn_results),
                tool_calls_used=tool_calls_count,
                elapsed_ms=max(0, int((self._clock() - started_at) * 1000)),
            )
            decision = evaluate_run_limits(request.limits, state)
            if not decision.allowed:
                stop_reason = decision.limit_name or "run_limit"
                break

            turn_index = request.turn_offset + len(turn_results) + 1
            turn_id = str(self._id_generator.turn_id())
            tool_executor = self._guarded_tool_executor(
                request.limits,
                tool_signatures=tool_signatures,
                tool_calls_used=tool_calls_count,
            )
            turn_kernel = TurnKernel(
                llm_client=self._llm_client,
                event_writer=self._event_writer,
                tool_executor=tool_executor,
                tool_observability=self._tool_observability,
                tool_policy=self._tool_policy,
            )
            turn_result = await turn_kernel.run_turn(
                TurnRequest(
                    run_id=request.run_id,
                    turn_id=turn_id,
                    messages=tuple(messages),
                    tool_context=request.tool_context,
                    model=request.model,
                    system_prompt=request.system_prompt,
                    tools=request.tools,
                    turn_index=turn_index,
                    metadata=request.metadata,
                    cancellation_token=request.cancellation_token,
                )
            )

            turn_results.append(turn_result)
            all_events.extend(turn_result.events)
            all_tool_results.extend(turn_result.tool_results)
            tool_calls_count += turn_result.tool_calls_executed
            usage = _add_usage(usage, turn_result.usage)
            messages.extend(
                build_messages_after_turn(
                    turn_id=turn_id,
                    assistant_message_id=str(self._id_generator.message_id()),
                    content=turn_result.content,
                    tool_results=turn_result.tool_results,
                    id_generator=self._id_generator,
                )
            )
            stop_reason = turn_result.stop_reason

            if _has_repeated_tool_call_denial(turn_result.tool_results):
                stop_reason = "repeated_tool_call"
                break
            if turn_result.stop_reason == CoreErrorType.CANCELLED.value:
                break
            if turn_result.pause_requested or turn_result.tool_calls_executed == 0:
                break

        return RunKernelResult(
            stop_reason=stop_reason,
            messages=tuple(messages),
            turns_count=len(turn_results),
            tool_calls_count=tool_calls_count,
            usage=usage,
            turn_results=tuple(turn_results),
            events=tuple(all_events),
            tool_results=tuple(all_tool_results),
        )

    def _guarded_tool_executor(
        self,
        limits: RunLimits,
        *,
        tool_signatures: list[ToolCallSignature],
        tool_calls_used: int,
    ) -> ToolExecutorLike | None:
        executor = self._tool_executor
        if executor is None:
            return None
        if limits.max_tool_calls is not None:
            executor = _MaxToolCallsGuard(
                executor=executor,
                max_tool_calls=limits.max_tool_calls,
                tool_calls_used=tool_calls_used,
            )
        if limits.repeated_tool_call_threshold is not None:
            executor = _RepeatedToolCallGuard(
                executor=executor,
                signatures=tool_signatures,
                threshold=limits.repeated_tool_call_threshold,
            )
        return executor


class _MaxToolCallsGuard:
    def __init__(
        self,
        *,
        executor: ToolExecutorLike,
        max_tool_calls: int,
        tool_calls_used: int,
    ) -> None:
        if max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")
        if tool_calls_used < 0:
            raise ValueError("tool_calls_used must be >= 0")
        self._executor = executor
        self._max_tool_calls = max_tool_calls
        self._tool_calls_seen = tool_calls_used

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        if self._tool_calls_seen >= self._max_tool_calls:
            return ToolExecutionResult(
                ok=False,
                content="Tool call blocked by run policy: max_tool_calls reached.",
                error=core_error(
                    CoreErrorType.MAX_TOOL_CALLS.value,
                    "Tool call blocked by run policy: max_tool_calls reached.",
                    details={
                        "tool_name": request.tool_name,
                        "tool_use_id": request.tool_use_id,
                    },
                ),
            )

        self._tool_calls_seen += 1
        raw_result = self._executor.execute_tool(request)
        return await raw_result if inspect.isawaitable(raw_result) else raw_result


class _RepeatedToolCallGuard:
    def __init__(
        self,
        *,
        executor: ToolExecutorLike,
        signatures: list[ToolCallSignature],
        threshold: int,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        self._executor = executor
        self._signatures = signatures
        self._threshold = threshold

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        candidate = tool_call_signature(request.tool_name, request.tool_input)
        occurrences_including_current = (
            sum(1 for signature in self._signatures if signature == candidate) + 1
        )
        if occurrences_including_current >= self._threshold:
            return ToolExecutionResult(
                ok=False,
                content="Repeated tool call blocked by run policy.",
                error=core_error(
                    CoreErrorType.REPEATED_TOOL_CALL.value,
                    "Repeated tool call blocked by run policy.",
                    details={
                        "tool_name": request.tool_name,
                        "tool_use_id": request.tool_use_id,
                    },
                ),
            )

        self._signatures.append(candidate)
        raw_result = self._executor.execute_tool(request)
        return await raw_result if inspect.isawaitable(raw_result) else raw_result


def build_messages_after_turn(
    *,
    turn_id: str,
    assistant_message_id: str,
    content: tuple[StandardContentBlock, ...],
    tool_results: tuple[ToolExecutionResult, ...],
    id_generator: IdGenerator | None = None,
) -> tuple[Message, ...]:
    ids = id_generator or UuidIdGenerator()
    tool_calls = tuple(block for block in content if isinstance(block, ToolUseBlock))
    if len(tool_calls) != len(tool_results):
        raise ValueError("tool_results must pair one-to-one with tool_use content blocks")
    messages = [
        Message(
            message_id=assistant_message_id,
            role="assistant",
            content=[asdict(block) for block in content],
            turn_id=turn_id,
            tool_calls=[
                ToolCall(
                    tool_use_id=block.id,
                    tool_name=block.name,
                    input=dict(block.input),
                    status=ToolCallStatus.COMPLETE,
                )
                for block in tool_calls
            ],
        )
    ]

    for tool_call, result in zip(tool_calls, tool_results, strict=True):
        tool_result = ToolResult(
            tool_use_id=tool_call.id,
            ok=result.ok,
            content=result.content,
            error=result.error,
        )
        messages.append(
            Message(
                message_id=str(ids.message_id()),
                role="tool",
                content=result.content,
                turn_id=turn_id,
                tool_results=[tool_result],
            )
        )
    return tuple(messages)


def _has_repeated_tool_call_denial(
    tool_results: tuple[ToolExecutionResult, ...],
) -> bool:
    return any(
        result.error is not None and result.error.get("type") == "repeated_tool_call"
        for result in tool_results
    )


def _add_usage(left: Usage, right: Usage) -> Usage:
    return Usage(
        input_tokens=left.input_tokens + right.input_tokens,
        output_tokens=left.output_tokens + right.output_tokens,
        cache_creation_input_tokens=(
            left.cache_creation_input_tokens + right.cache_creation_input_tokens
        ),
        cache_read_input_tokens=left.cache_read_input_tokens + right.cache_read_input_tokens,
    )


def _is_cancelled(token: CancellationToken | None) -> bool:
    return token is not None and token.is_cancelled()
