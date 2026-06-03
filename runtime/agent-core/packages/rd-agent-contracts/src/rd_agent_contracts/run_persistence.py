"""Host-neutral AgentRun persistence contracts.

This module describes the run lifecycle data that a product host must persist
for bounded agent execution slices. It intentionally avoids ORM, queue, and
product-specific model types so SaaS, local, or future PaaS hosts can implement
the same adapter boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from .usage import Usage, normalize_usage


class AgentKind(StrEnum):
    ORCHESTRATOR = "orchestrator"
    SUBAGENT = "subagent"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    CONTINUABLE = "continuable"
    WAITING_USER = "waiting_user"
    RESUMING = "resuming"
    RESUMED = "resumed"
    NEEDS_ATTENTION = "needs_attention"
    FAILED = "failed"


@dataclass(frozen=True)
class RunBudget:
    max_turns: int
    max_tool_calls: int
    max_wall_clock_s: int
    total_timeout_s: int

    def __post_init__(self) -> None:
        for field_name in (
            "max_turns",
            "max_tool_calls",
            "max_wall_clock_s",
            "total_timeout_s",
        ):
            if getattr(self, field_name) < 1:
                raise ValueError(f"{field_name} must be >= 1")

    def to_json(self) -> dict[str, int]:
        return {
            "max_turns": self.max_turns,
            "max_tool_calls": self.max_tool_calls,
            "max_wall_clock_s": self.max_wall_clock_s,
            "total_timeout_s": self.total_timeout_s,
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> RunBudget:
        return cls(
            max_turns=int(raw["max_turns"]),
            max_tool_calls=int(raw["max_tool_calls"]),
            max_wall_clock_s=int(raw["max_wall_clock_s"]),
            total_timeout_s=int(raw["total_timeout_s"]),
        )


@dataclass(frozen=True)
class RunScope:
    user_request_id: str
    project_id: str
    session_id: str | None = None
    parent_run_id: str | None = None
    subagent_task_id: str | None = None
    agent_kind: str = AgentKind.ORCHESTRATOR
    correlation_id: str | None = None


@dataclass(frozen=True)
class RunResultMetadata:
    usage: Usage = field(default_factory=Usage)
    turns_count: int = 0
    tool_calls_count: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        payload: dict[str, Any] = dict(self.extra)
        payload.update({
            "usage": {
                "input_tokens": self.usage.input_tokens,
                "output_tokens": self.usage.output_tokens,
                "cache_creation_input_tokens": self.usage.cache_creation_input_tokens,
                "cache_read_input_tokens": self.usage.cache_read_input_tokens,
            },
            "turns_count": self.turns_count,
            "tool_calls_count": self.tool_calls_count,
        })
        return payload

    @classmethod
    def from_json(cls, raw: Mapping[str, Any] | None) -> RunResultMetadata:
        if raw is None:
            return cls()
        known_keys = {"usage", "turns_count", "tool_calls_count"}
        return cls(
            usage=normalize_usage(raw.get("usage")),
            turns_count=int(raw.get("turns_count", 0) or 0),
            tool_calls_count=int(raw.get("tool_calls_count", 0) or 0),
            extra={key: value for key, value in raw.items() if key not in known_keys},
        )


@dataclass(frozen=True)
class RunCompletion:
    stop_reason: str
    metadata: RunResultMetadata = field(default_factory=RunResultMetadata)
    engine_state_json: str | None = None
    completed_at_ms: int | None = None


@dataclass(frozen=True)
class RunFailure:
    error_message: str
    completed_at_ms: int | None = None


@dataclass(frozen=True)
class RunRecord:
    run_id: str
    scope: RunScope
    status: str
    run_index: int
    continuation_index: int
    max_continuations: int
    budget: RunBudget | None = None
    stop_reason: str | None = None
    error_message: str | None = None
    result_metadata: RunResultMetadata = field(default_factory=RunResultMetadata)
    engine_state_json: str | None = None
    created_at_ms: int | None = None
    started_at_ms: int | None = None
    completed_at_ms: int | None = None


@runtime_checkable
class RunPersistencePort(Protocol):
    """Persistence boundary for AgentRun lifecycle state.

    Implementations own transaction scope. Methods that combine run updates with
    queue, session, request, or subagent state should be composed by the host
    adapter without leaking those host models into this protocol.
    """

    def create_root_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord: ...

    def create_subagent_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord: ...

    def create_continuation_run(
        self,
        *,
        previous_run_id: str,
        engine_state_json: str,
        run_id: str | None = None,
    ) -> RunRecord | None: ...

    def mark_running(
        self,
        run_id: str,
        *,
        started_at_ms: int | None = None,
    ) -> RunRecord | None: ...

    def mark_completed(
        self,
        run_id: str,
        *,
        completion: RunCompletion,
    ) -> RunRecord | None: ...

    def mark_failed(
        self,
        run_id: str,
        *,
        failure: RunFailure,
    ) -> RunRecord | None: ...

    def mark_resumed(self, run_id: str) -> RunRecord | None: ...

    def claim_latest_waiting_orchestrator_run(
        self,
        *,
        project_id: str,
    ) -> RunRecord | None: ...

    def load_run(self, run_id: str) -> RunRecord | None: ...

    def load_run_with_parent(
        self,
        run_id: str,
    ) -> tuple[RunRecord, RunRecord | None] | None: ...
