"""Host-neutral Agent timeline read-model contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class TimelineRequest:
    request_id: str
    project_id: str
    session_id: str | None
    instruction: str
    request_type: str | None = None
    status: str | None = None
    is_completed: bool | None = None
    is_successful: bool | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    created_at_ms: int | None = None
    started_at_ms: int | None = None
    completed_at_ms: int | None = None


@dataclass(frozen=True)
class TimelineRun:
    run_id: str
    user_request_id: str
    project_id: str
    session_id: str | None
    agent_kind: str
    status: str
    parent_run_id: str | None = None
    subagent_task_id: str | None = None
    run_index: int = 1
    stop_reason: str | None = None
    error_message: str | None = None
    continuation_index: int = 0
    max_continuations: int = 0
    budget_json: dict[str, Any] | None = None
    result_metadata_json: dict[str, Any] | None = None
    correlation_id: str | None = None
    created_at_ms: int | None = None
    started_at_ms: int | None = None
    completed_at_ms: int | None = None


@dataclass(frozen=True)
class TimelineSubagentTask:
    task_id: str
    user_request_id: str
    project_id: str
    name: str
    description: str
    status: str
    parent_run_id: str | None = None
    agent_profile: str | None = None
    attempts: int = 0
    max_attempts: int = 3
    worker_id: str | None = None
    write_scope_json: dict[str, Any] | None = None
    depends_on_task_ids: list[str] = field(default_factory=list)
    result_summary: str | None = None
    outcome_json: dict[str, Any] | None = None
    error_message: str | None = None
    correlation_id: str | None = None
    created_at_ms: int | None = None
    available_at_ms: int | None = None
    started_at_ms: int | None = None
    heartbeat_at_ms: int | None = None
    completed_at_ms: int | None = None
    dispatch_mode: str | None = None
    parallel_group_id: str | None = None
    blocked_reason: str | None = None
    write_scope_paths: list[str] = field(default_factory=list)
    workspace_mode: str | None = None
    merge_strategy: str | None = None
    merge_status: str | None = None
    merge_conflict_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AgentTimeline:
    project_id: str
    request: TimelineRequest
    runs: list[TimelineRun] = field(default_factory=list)
    subagent_tasks: list[TimelineSubagentTask] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class TimelineReadPort(Protocol):
    """Product-facing read-model boundary for Agent progress/timeline UI."""

    def load_agent_timeline(
        self,
        *,
        project_id: str,
        request_id: str | None = None,
    ) -> AgentTimeline | None: ...
