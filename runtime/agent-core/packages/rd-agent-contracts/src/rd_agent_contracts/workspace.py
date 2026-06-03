"""Host-neutral workspace isolation contracts for subagents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .subagent import normalize_write_scope_paths


@dataclass(frozen=True)
class SubagentWorkspaceSpec:
    project_id: str
    task_id: str
    run_id: str
    write_scope_json: dict[str, Any] | None = None


@dataclass(frozen=True)
class SubagentWorkspaceIsolationDecision:
    enabled: bool
    write_scope_paths: list[str]
    reason: str | None = None


@dataclass(frozen=True)
class SubagentWorkspaceMergeResult:
    changed: bool
    merged_paths: list[str]
    generation: int | None = None


@runtime_checkable
class SubagentWorkspaceHandle(Protocol):
    project_id: str
    task_id: str
    run_id: str
    write_scope_paths: list[str]

    def merge_back(
        self,
        *,
        cleanup: bool = True,
    ) -> SubagentWorkspaceMergeResult: ...

    def cleanup(self) -> None: ...


@runtime_checkable
class SubagentWorkspacePort(Protocol):
    def prepare_workspace(
        self,
        spec: SubagentWorkspaceSpec,
    ) -> SubagentWorkspaceHandle: ...


def decide_subagent_workspace_isolation(
    *,
    agent_kind: str,
    write_scope_json: dict[str, Any] | None,
    workspace_isolation_enabled: bool,
    inline_parallel_enabled: bool,
) -> SubagentWorkspaceIsolationDecision:
    """Decide whether a child agent should run in an isolated workspace.

    The decision is intentionally ordered from broad host capability gates to
    task-specific scope availability. ``reason`` identifies the first gate that
    disabled isolation so callers can distinguish a configured-off runtime from
    a subagent task that simply has no write scope.
    """

    scope_paths = normalize_write_scope_paths(write_scope_json)
    if agent_kind != "subagent":
        return SubagentWorkspaceIsolationDecision(
            enabled=False,
            write_scope_paths=scope_paths,
            reason="agent_kind_not_subagent",
        )
    if not workspace_isolation_enabled:
        return SubagentWorkspaceIsolationDecision(
            enabled=False,
            write_scope_paths=scope_paths,
            reason="workspace_isolation_disabled",
        )
    if not inline_parallel_enabled:
        return SubagentWorkspaceIsolationDecision(
            enabled=False,
            write_scope_paths=scope_paths,
            reason="inline_parallel_disabled",
        )
    if not scope_paths:
        return SubagentWorkspaceIsolationDecision(
            enabled=False,
            write_scope_paths=[],
            reason="write_scope_empty",
        )
    return SubagentWorkspaceIsolationDecision(
        enabled=True,
        write_scope_paths=scope_paths,
        reason=None,
    )


def should_merge_subagent_workspace(
    *,
    will_queue_continuation: bool,
    needs_attention: bool,
    retryable_needs_attention: bool,
) -> bool:
    if will_queue_continuation:
        return True
    if not needs_attention:
        return True
    return retryable_needs_attention
