from __future__ import annotations

import pytest
from rd_agent_contracts import (
    AgentKind,
    ContinuationJobSpec,
    ContinuationJobStatus,
    EventDraft,
    RunBudget,
    RunCompletion,
    RunScope,
    RunStatus,
)
from rd_agent_core.conformance import (
    assert_event_log_port_conformance,
    assert_run_persistence_port_conformance,
)

from examples.reference_host import connect_sqlite_reference_host
from examples.reference_host.continuation_worker import ReferenceContinuationWorker
from examples.reference_host.demo import run_demo


def test_sqlite_event_log_preserves_sequence_and_idempotency() -> None:
    host = connect_sqlite_reference_host()
    try:
        first = host.event_log.append_event(
            "run-1",
            EventDraft(event_type="turn_started", payload={"attempt": 1}),
            idempotency_key="turn-1:start",
        )
        replay = host.event_log.append_event(
            "run-1",
            EventDraft(event_type="turn_started", payload={"attempt": 2}),
            idempotency_key="turn-1:start",
        )
        second = host.event_log.append_event(
            "run-1",
            EventDraft(event_type="turn_completed", payload={"ok": True}),
        )

        assert replay == first
        assert first.seq == 1
        assert second.seq == 2
        assert [event.seq for event in host.event_log.stream_events("run-1")] == [1, 2]
    finally:
        host.close()


def test_sqlite_run_persistence_links_continuation_parent() -> None:
    host = connect_sqlite_reference_host()
    try:
        budget = RunBudget(
            max_turns=2,
            max_tool_calls=2,
            max_wall_clock_s=30,
            total_timeout_s=60,
        )
        root = host.persistence.create_root_run(
            run_id="run-root",
            scope=RunScope(user_request_id="request-1", project_id="project-1"),
            budget=budget,
            max_continuations=1,
        )
        continuation = host.persistence.create_continuation_run(
            previous_run_id=root.run_id,
            engine_state_json='{"cursor":1}',
            run_id="run-cont-1",
        )
        overflow = host.persistence.create_continuation_run(
            previous_run_id="run-cont-1",
            engine_state_json='{"cursor":2}',
            run_id="run-cont-2",
        )

        assert continuation is not None
        assert continuation.scope.parent_run_id == root.run_id
        assert continuation.engine_state_json == '{"cursor":1}'
        assert host.persistence.load_run_with_parent("run-cont-1") == (
            continuation,
            root,
        )
        assert overflow is None
    finally:
        host.close()


def test_sqlite_run_persistence_claims_latest_waiting_orchestrator_run() -> None:
    host = connect_sqlite_reference_host()
    try:
        budget = RunBudget(
            max_turns=2,
            max_tool_calls=2,
            max_wall_clock_s=30,
            total_timeout_s=60,
        )
        host.persistence.create_root_run(
            run_id="run-old",
            scope=RunScope(
                user_request_id="request-1",
                project_id="project-1",
                agent_kind=AgentKind.ORCHESTRATOR,
            ),
            budget=budget,
        )
        latest = host.persistence.create_root_run(
            run_id="run-latest",
            scope=RunScope(
                user_request_id="request-2",
                project_id="project-1",
                agent_kind=AgentKind.ORCHESTRATOR,
            ),
            budget=budget,
        )
        host.persistence.create_root_run(
            run_id="run-other-project",
            scope=RunScope(
                user_request_id="request-3",
                project_id="project-2",
                agent_kind=AgentKind.ORCHESTRATOR,
            ),
            budget=budget,
        )
        host.persistence.mark_completed(
            "run-old",
            completion=RunCompletion(stop_reason="end_turn"),
        )
        host.persistence.mark_waiting_user("run-latest")
        host.persistence.mark_waiting_user("run-other-project")

        claimed = host.persistence.claim_latest_waiting_orchestrator_run(
            project_id="project-1"
        )

        assert claimed is not None
        assert claimed.run_id == latest.run_id
        assert claimed.status == RunStatus.RESUMING
    finally:
        host.close()


async def test_reference_host_demo_runs_end_to_end() -> None:
    summary = await run_demo()

    assert summary["status"] == RunStatus.COMPLETED
    assert summary["stop_reason"] == "end_turn"
    assert summary["turns_count"] == 2
    assert summary["tool_calls_count"] == 1
    assert summary["event_count"] > 0
    assert "tool_completed" in summary["event_types"]


def test_sqlite_run_persistence_rejects_duplicate_run_id() -> None:
    host = connect_sqlite_reference_host()
    try:
        budget = RunBudget(
            max_turns=1,
            max_tool_calls=1,
            max_wall_clock_s=30,
            total_timeout_s=60,
        )
        scope = RunScope(user_request_id="request-1", project_id="project-1")
        host.persistence.create_root_run(run_id="run-1", scope=scope, budget=budget)

        with pytest.raises(ValueError, match="run_id already exists"):
            host.persistence.create_root_run(
                run_id="run-1",
                scope=scope,
                budget=budget,
            )
    finally:
        host.close()


def test_sqlite_ports_pass_core_conformance_checks() -> None:
    host = connect_sqlite_reference_host()
    try:
        assert_event_log_port_conformance(host.event_log)
        assert_run_persistence_port_conformance(host.persistence)
    finally:
        host.close()


def test_sqlite_continuation_queue_claims_retries_and_dead_letters() -> None:
    host = connect_sqlite_reference_host()
    try:
        job = host.continuation_queue.enqueue_for_run(
            ContinuationJobSpec(
                user_request_id="request-1",
                project_id="project-1",
                previous_run_id="run-1",
                next_run_id="run-2",
                max_attempts=2,
            ),
            job_id="job-1",
        )

        claimed = host.continuation_queue.claim_next(worker_id="worker-1")
        assert claimed is not None
        assert claimed.job_id == job.job_id
        assert claimed.status == ContinuationJobStatus.RUNNING
        started = host.continuation_queue.mark_attempt_started(job.job_id)
        assert started is not None
        assert started.attempts == 1

        retry = host.continuation_queue.complete_failure(
            job.job_id,
            error="temporary",
            retry_available_at_ms=1,
        )
        assert retry is not None
        assert retry.status == ContinuationJobStatus.QUEUED
        assert retry.last_error == "temporary"

        claimed_again = host.continuation_queue.claim_next(
            worker_id="worker-2",
            available_at_ms=2,
        )
        assert claimed_again is not None
        host.continuation_queue.mark_attempt_started(job.job_id)
        dead = host.continuation_queue.complete_failure(job.job_id, error="final")
        assert dead is not None
        assert dead.status == ContinuationJobStatus.DEAD_LETTER
        assert dead.last_error == "final"
    finally:
        host.close()


async def test_reference_continuation_worker_completes_claimed_job() -> None:
    host = connect_sqlite_reference_host()
    handled: list[str] = []
    try:
        host.continuation_queue.enqueue_for_run(
            ContinuationJobSpec(
                user_request_id="request-1",
                project_id="project-1",
                previous_run_id="run-1",
                next_run_id="run-2",
            ),
            job_id="job-worker",
        )
        worker = ReferenceContinuationWorker(
            queue=host.continuation_queue,
            worker_id="worker-1",
            handler=lambda job: handled.append(job.job_id),
        )

        completed = await worker.run_once()

        assert completed is not None
        assert completed.status == ContinuationJobStatus.SUCCEEDED
        assert completed.attempts == 1
        assert handled == ["job-worker"]
    finally:
        host.close()
