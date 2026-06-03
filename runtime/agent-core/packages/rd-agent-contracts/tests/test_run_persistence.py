from __future__ import annotations

from rd_agent_contracts.run_persistence import (
    AgentKind,
    RunBudget,
    RunCompletion,
    RunFailure,
    RunPersistencePort,
    RunRecord,
    RunResultMetadata,
    RunScope,
    RunStatus,
)
from rd_agent_contracts.usage import Usage


def test_run_budget_json_roundtrip():
    budget = RunBudget(
        max_turns=80,
        max_tool_calls=120,
        max_wall_clock_s=1800,
        total_timeout_s=3600,
    )

    assert RunBudget.from_json(budget.to_json()) == budget


def test_run_budget_rejects_non_positive_limits():
    try:
        RunBudget(
            max_turns=0,
            max_tool_calls=120,
            max_wall_clock_s=1800,
            total_timeout_s=3600,
        )
    except ValueError as exc:
        assert "max_turns" in str(exc)
    else:
        raise AssertionError("expected max_turns validation failure")


def test_result_metadata_json_roundtrip_preserves_extra_fields():
    metadata = RunResultMetadata(
        usage=Usage(input_tokens=10, output_tokens=5),
        turns_count=3,
        tool_calls_count=2,
        extra={"provider": "anthropic"},
    )

    restored = RunResultMetadata.from_json(metadata.to_json())

    assert restored.usage.total() == 15
    assert restored.turns_count == 3
    assert restored.tool_calls_count == 2
    assert restored.extra == {"provider": "anthropic"}


def test_run_record_carries_host_neutral_scope():
    record = RunRecord(
        run_id="run_1",
        scope=RunScope(
            user_request_id="req_1",
            project_id="proj_1",
            session_id="sess_1",
            agent_kind=AgentKind.ORCHESTRATOR,
            correlation_id="corr_1",
        ),
        status=RunStatus.PENDING,
        run_index=1,
        continuation_index=0,
        max_continuations=2,
        budget=RunBudget(
            max_turns=80,
            max_tool_calls=120,
            max_wall_clock_s=1800,
            total_timeout_s=3600,
        ),
        created_at_ms=1710000000000,
    )

    assert record.scope.subagent_task_id is None
    assert record.status == "pending"
    assert record.budget and record.budget.max_turns == 80


class _StubRunPersistencePort:
    def __init__(self) -> None:
        self.records: dict[str, RunRecord] = {}

    def create_root_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        record = RunRecord(
            run_id=run_id or "run_root",
            scope=scope,
            status=RunStatus.PENDING,
            run_index=1,
            continuation_index=0,
            max_continuations=max_continuations,
            budget=budget,
        )
        self.records[record.run_id] = record
        return record

    def create_subagent_run(
        self,
        *,
        scope: RunScope,
        budget: RunBudget,
        max_continuations: int = 0,
        run_id: str | None = None,
    ) -> RunRecord:
        record = RunRecord(
            run_id=run_id or "run_subagent",
            scope=scope,
            status=RunStatus.PENDING,
            run_index=1,
            continuation_index=0,
            max_continuations=max_continuations,
            budget=budget,
        )
        self.records[record.run_id] = record
        return record

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
        record = RunRecord(
            run_id=run_id or "run_continuation",
            scope=RunScope(
                user_request_id=previous.scope.user_request_id,
                project_id=previous.scope.project_id,
                session_id=previous.scope.session_id,
                parent_run_id=previous.run_id,
                subagent_task_id=previous.scope.subagent_task_id,
                agent_kind=previous.scope.agent_kind,
                correlation_id=previous.scope.correlation_id,
            ),
            status=RunStatus.PENDING,
            run_index=previous.run_index + 1,
            continuation_index=previous.continuation_index + 1,
            max_continuations=previous.max_continuations,
            budget=previous.budget,
            engine_state_json=engine_state_json,
        )
        self.records[record.run_id] = record
        return record

    def mark_running(
        self,
        run_id: str,
        *,
        started_at_ms: int | None = None,
    ) -> RunRecord | None:
        return self.records.get(run_id)

    def mark_completed(
        self,
        run_id: str,
        *,
        completion: RunCompletion,
    ) -> RunRecord | None:
        return self.records.get(run_id)

    def mark_failed(
        self,
        run_id: str,
        *,
        failure: RunFailure,
    ) -> RunRecord | None:
        return self.records.get(run_id)

    def mark_resumed(self, run_id: str) -> RunRecord | None:
        return self.records.get(run_id)

    def claim_latest_waiting_orchestrator_run(
        self,
        *,
        project_id: str,
    ) -> RunRecord | None:
        return next(
            (
                record
                for record in self.records.values()
                if record.scope.project_id == project_id
            ),
            None,
        )

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


def test_run_persistence_port_protocol_is_runtime_checkable():
    port: RunPersistencePort = _StubRunPersistencePort()

    assert isinstance(port, RunPersistencePort)

    budget = RunBudget(
        max_turns=80,
        max_tool_calls=120,
        max_wall_clock_s=1800,
        total_timeout_s=3600,
    )
    root = port.create_root_run(
        scope=RunScope(user_request_id="req_1", project_id="proj_1"),
        budget=budget,
        max_continuations=1,
    )
    continuation = port.create_continuation_run(
        previous_run_id=root.run_id,
        engine_state_json="[]",
    )

    assert continuation is not None
    assert continuation.scope.parent_run_id == root.run_id
