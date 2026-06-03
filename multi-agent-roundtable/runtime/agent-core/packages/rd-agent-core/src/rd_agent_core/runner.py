"""High-level runner facade for hosts that want lifecycle glue included."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from rd_agent_contracts import (
    AgentEvent,
    CancellationToken,
    EventLogPort,
    IdGenerator,
    Message,
    RunBudget,
    RunCompletion,
    RunFailure,
    RunPersistencePort,
    RunRecord,
    RunResultMetadata,
    RunScope,
    ToolDefinition,
    ToolExecutionContext,
    ToolObservabilityPort,
)

from .events import CoreEventWriter
from .observability import RunObserverLike, notify_run_observer
from .policies import RunLimits
from .run import RunKernel, RunKernelResult, RunRequest
from .summary import RunSummary, summarize_failed_run, summarize_kernel_result
from .turn import CoreToolPolicy, LLMClientPort, ToolExecutorLike


@dataclass(frozen=True)
class AgentRunnerRequest:
    scope: RunScope
    budget: RunBudget
    messages: Sequence[Message] = ()
    tools: Sequence[ToolDefinition] = ()
    tool_context: ToolExecutionContext | None = None
    run_id: str | None = None
    max_continuations: int = 0
    model: str | None = None
    system_prompt: str | None = None
    limits: RunLimits | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    cancellation_token: CancellationToken | None = None


@dataclass(frozen=True)
class AgentRunnerResult:
    run: RunRecord
    completed: RunRecord
    kernel_result: RunKernelResult
    events: tuple[AgentEvent, ...]
    summary: RunSummary


class AgentRunner:
    """Small facade that wires run persistence around ``RunKernel``.

    The runner owns no transactions beyond calling host ports in order. Hosts
    that need stronger atomicity can either wrap their port implementation in a
    transaction or keep using ``RunKernel`` directly.
    """

    def __init__(
        self,
        *,
        run_persistence: RunPersistencePort,
        event_log: EventLogPort,
        llm_client: LLMClientPort,
        tool_executor: ToolExecutorLike | None = None,
        tool_observability: ToolObservabilityPort | None = None,
        tool_policy: CoreToolPolicy | None = None,
        run_observer: RunObserverLike | None = None,
        id_generator: IdGenerator | None = None,
    ) -> None:
        self._run_persistence = run_persistence
        self._event_log = event_log
        self._llm_client = llm_client
        self._tool_executor = tool_executor
        self._tool_observability = tool_observability
        self._tool_policy = tool_policy
        self._run_observer = run_observer
        self._id_generator = id_generator

    async def run(self, request: AgentRunnerRequest) -> AgentRunnerResult:
        run = self._run_persistence.create_root_run(
            scope=request.scope,
            budget=request.budget,
            max_continuations=request.max_continuations,
            run_id=request.run_id,
        )
        running = self._run_persistence.mark_running(run.run_id)
        if running is None:
            raise RuntimeError(f"created run cannot be marked running: {run.run_id}")

        try:
            kernel = RunKernel(
                llm_client=self._llm_client,
                event_writer=CoreEventWriter(self._event_log, run_id=run.run_id),
                tool_executor=self._tool_executor,
                tool_observability=self._tool_observability,
                tool_policy=self._tool_policy,
                id_generator=self._id_generator,
            )
            kernel_result = await kernel.run(
                RunRequest(
                    run_id=run.run_id,
                    messages=tuple(request.messages),
                    tool_context=self._resolve_tool_context(request, run_id=run.run_id),
                    tools=tuple(request.tools),
                    model=request.model,
                    system_prompt=request.system_prompt,
                    limits=request.limits or _limits_from_budget(request.budget),
                    metadata=dict(request.metadata),
                    cancellation_token=request.cancellation_token,
                )
            )
            events = tuple(self._event_log.stream_events(run.run_id))
            completed = self._run_persistence.mark_completed(
                run.run_id,
                completion=RunCompletion(
                    stop_reason=kernel_result.stop_reason,
                    metadata=RunResultMetadata(
                        usage=kernel_result.usage,
                        turns_count=kernel_result.turns_count,
                        tool_calls_count=kernel_result.tool_calls_count,
                        extra={"event_count": len(kernel_result.events)},
                    ),
                ),
            )
            if completed is None:
                raise RuntimeError(f"completed run disappeared: {run.run_id}")
            summary = summarize_kernel_result(
                run_id=run.run_id,
                status=str(completed.status),
                kernel_result=kernel_result,
                events=events,
            )
            await notify_run_observer(self._run_observer, summary)
            return AgentRunnerResult(
                run=run,
                completed=completed,
                kernel_result=kernel_result,
                events=events,
                summary=summary,
            )
        except Exception as exc:
            self._run_persistence.mark_failed(
                run.run_id,
                failure=RunFailure(error_message=str(exc)),
            )
            summary = summarize_failed_run(
                run_id=run.run_id,
                error_message=str(exc),
                events=self._event_log.stream_events(run.run_id),
            )
            await notify_run_observer(self._run_observer, summary)
            raise

    def _resolve_tool_context(
        self,
        request: AgentRunnerRequest,
        *,
        run_id: str,
    ) -> ToolExecutionContext:
        if request.tool_context is not None:
            return request.tool_context
        return ToolExecutionContext(
            project_id=request.scope.project_id,
            correlation_id=request.scope.correlation_id,
            session_id=request.scope.session_id,
            user_request_id=request.scope.user_request_id,
            agent_run_id=run_id,
            agent_kind=str(request.scope.agent_kind),
            subagent_task_id=request.scope.subagent_task_id,
        )


def _limits_from_budget(budget: RunBudget) -> RunLimits:
    return RunLimits(
        max_turns=budget.max_turns,
        max_tool_calls=budget.max_tool_calls,
        timeout_ms=budget.max_wall_clock_s * 1000,
    )
