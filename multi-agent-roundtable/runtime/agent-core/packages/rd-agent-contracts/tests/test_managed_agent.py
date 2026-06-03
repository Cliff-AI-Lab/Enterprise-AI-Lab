from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rd_agent_contracts import (
    AgentEvent,
    ManagedAgentEventReadPort,
    ManagedAgentEventReplay,
    ManagedAgentRecoveryAssessment,
    ManagedAgentRecoveryPort,
)


class _ManagedAgentPort:
    def replay_events(
        self,
        *,
        managed_session_id: str,
        cursor: Mapping[str, int] | None = None,
        limit: int | None = None,
    ) -> ManagedAgentEventReplay:
        return ManagedAgentEventReplay(
            managed_session_id=managed_session_id,
            run_ids=("run-1",),
            events=(
                AgentEvent(
                    seq=1,
                    timestamp_ms=123,
                    run_id="run-1",
                    turn_id="turn-1",
                    event_type="turn_started",
                    payload={"cursor": dict(cursor or {})},
                ),
            ),
            next_cursor={"run-1": 1},
        )

    def tail_events(
        self,
        *,
        managed_session_id: str,
        after_cursor: Mapping[str, int] | None = None,
        limit: int | None = None,
    ) -> ManagedAgentEventReplay:
        return self.replay_events(
            managed_session_id=managed_session_id,
            cursor=after_cursor,
            limit=limit,
        )

    def assess_recovery(
        self,
        *,
        managed_session_id: str,
        stale_after_seconds: int,
    ) -> ManagedAgentRecoveryAssessment:
        return ManagedAgentRecoveryAssessment(
            managed_session_id=managed_session_id,
            needs_recovery=True,
            reason="stale_running_run",
            session_status="running",
            run_id="run-1",
            run_status="running",
        )

    def mark_recovery_required(
        self,
        *,
        managed_session_id: str,
        reason: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        return None


def test_managed_agent_contracts_are_runtime_checkable() -> None:
    port = _ManagedAgentPort()

    assert isinstance(port, ManagedAgentEventReadPort)
    assert isinstance(port, ManagedAgentRecoveryPort)
    assert port.tail_events(
        managed_session_id="session-1",
        after_cursor={"run-1": 0},
    ).next_cursor == {"run-1": 1}
    assert port.assess_recovery(
        managed_session_id="session-1",
        stale_after_seconds=60,
    ).reason == "stale_running_run"
