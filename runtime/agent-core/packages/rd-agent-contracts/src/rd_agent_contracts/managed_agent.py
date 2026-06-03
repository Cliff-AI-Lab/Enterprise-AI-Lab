"""Host-neutral managed-agent platform contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .events import AgentEvent


@dataclass(frozen=True)
class ManagedAgentEventReplay:
    managed_session_id: str
    run_ids: tuple[str, ...]
    events: tuple[AgentEvent, ...]
    next_cursor: dict[str, int]


@dataclass(frozen=True)
class ManagedAgentRecoveryAssessment:
    managed_session_id: str
    needs_recovery: bool
    reason: str | None
    session_status: str | None
    run_id: str | None = None
    run_status: str | None = None
    metadata: Mapping[str, Any] | None = None


@runtime_checkable
class ManagedAgentEventReadPort(Protocol):
    """Session-level replay/tail boundary for managed-agent event streams."""

    def replay_events(
        self,
        *,
        managed_session_id: str,
        cursor: Mapping[str, int] | None = None,
        limit: int | None = None,
    ) -> ManagedAgentEventReplay: ...

    def tail_events(
        self,
        *,
        managed_session_id: str,
        after_cursor: Mapping[str, int] | None = None,
        limit: int | None = None,
    ) -> ManagedAgentEventReplay: ...


@runtime_checkable
class ManagedAgentRecoveryPort(Protocol):
    """Recovery assessment boundary for managed-agent sessions."""

    def assess_recovery(
        self,
        *,
        managed_session_id: str,
        stale_after_seconds: int,
    ) -> ManagedAgentRecoveryAssessment: ...

    def mark_recovery_required(
        self,
        *,
        managed_session_id: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None: ...
