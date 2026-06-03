from __future__ import annotations

import pytest
from rd_agent_contracts.continuation_queue import (
    ContinuationJobRecord,
    ContinuationJobSpec,
    ContinuationJobStatus,
    ContinuationQueuePort,
)


class _InMemoryContinuationQueue:
    def __init__(self) -> None:
        self._jobs: dict[str, ContinuationJobRecord] = {}
        self._next_id = 1
        self._clock_ms = 1_000

    def enqueue_for_run(
        self,
        spec: ContinuationJobSpec,
        *,
        job_id: str | None = None,
    ) -> ContinuationJobRecord:
        for job in self._jobs.values():
            if job.next_run_id == spec.next_run_id:
                return job

        job = ContinuationJobRecord(
            job_id=job_id or self._new_id(),
            user_request_id=spec.user_request_id,
            project_id=spec.project_id,
            previous_run_id=spec.previous_run_id,
            next_run_id=spec.next_run_id,
            status=ContinuationJobStatus.QUEUED,
            attempts=0,
            max_attempts=spec.max_attempts,
            correlation_id=spec.correlation_id,
            available_at_ms=spec.available_at_ms or self._now(),
            created_at_ms=self._now(),
            updated_at_ms=self._now(),
        )
        self._jobs[job.job_id] = job
        return job

    def claim_next(
        self,
        *,
        worker_id: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        timestamp_ms = available_at_ms or self._now()
        queued = [
            job
            for job in self._jobs.values()
            if job.status == ContinuationJobStatus.QUEUED
            and (job.available_at_ms or 0) <= timestamp_ms
        ]
        if not queued:
            return None
        job = sorted(queued, key=lambda item: item.created_at_ms or 0)[0]
        return self._replace(
            job.job_id,
            status=ContinuationJobStatus.RUNNING,
            worker_id=worker_id,
            locked_at_ms=timestamp_ms,
            heartbeat_at_ms=timestamp_ms,
            updated_at_ms=timestamp_ms,
        )

    def mark_attempt_started(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        job = self._jobs.get(job_id)
        if not job or job.status != ContinuationJobStatus.RUNNING:
            return None
        timestamp_ms = heartbeat_at_ms or self._now()
        return self._replace(
            job_id,
            attempts=job.attempts + 1,
            heartbeat_at_ms=timestamp_ms,
            updated_at_ms=timestamp_ms,
        )

    def heartbeat(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        if job_id not in self._jobs:
            return None
        timestamp_ms = heartbeat_at_ms or self._now()
        return self._replace(job_id, heartbeat_at_ms=timestamp_ms, updated_at_ms=timestamp_ms)

    def complete_success(
        self,
        job_id: str,
        *,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        if job_id not in self._jobs:
            return None
        timestamp_ms = completed_at_ms or self._now()
        return self._replace(
            job_id,
            status=ContinuationJobStatus.SUCCEEDED,
            completed_at_ms=timestamp_ms,
            updated_at_ms=timestamp_ms,
        )

    def complete_failure(
        self,
        job_id: str,
        *,
        error: str,
        retry_available_at_ms: int | None = None,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        timestamp_ms = completed_at_ms or self._now()
        if job.attempts >= job.max_attempts:
            return self._replace(
                job_id,
                status=ContinuationJobStatus.DEAD_LETTER,
                last_error=error,
                completed_at_ms=timestamp_ms,
                updated_at_ms=timestamp_ms,
            )
        return self.release_for_retry(
            job_id,
            error=error,
            available_at_ms=retry_available_at_ms or timestamp_ms,
        )

    def release_for_retry(
        self,
        job_id: str,
        *,
        error: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None:
        if job_id not in self._jobs:
            return None
        timestamp_ms = self._now()
        return self._replace(
            job_id,
            status=ContinuationJobStatus.QUEUED,
            worker_id=None,
            locked_at_ms=None,
            heartbeat_at_ms=None,
            last_error=error,
            available_at_ms=available_at_ms or timestamp_ms,
            updated_at_ms=timestamp_ms,
        )

    def reclaim_stale(self, *, stale_before_ms: int) -> int:
        reclaimed = 0
        for job in list(self._jobs.values()):
            if job.status != ContinuationJobStatus.RUNNING:
                continue
            if job.heartbeat_at_ms is not None and job.heartbeat_at_ms >= stale_before_ms:
                continue
            self.release_for_retry(
                job.job_id,
                error=job.last_error or "stale",
                available_at_ms=self._now(),
            )
            reclaimed += 1
        return reclaimed

    def load_job(self, job_id: str) -> ContinuationJobRecord | None:
        return self._jobs.get(job_id)

    def _new_id(self) -> str:
        job_id = f"job-{self._next_id}"
        self._next_id += 1
        return job_id

    def _now(self) -> int:
        self._clock_ms += 1
        return self._clock_ms

    def _replace(self, job_id: str, **changes) -> ContinuationJobRecord:
        old = self._jobs[job_id]
        payload = {
            "job_id": old.job_id,
            "user_request_id": old.user_request_id,
            "project_id": old.project_id,
            "previous_run_id": old.previous_run_id,
            "next_run_id": old.next_run_id,
            "status": old.status,
            "attempts": old.attempts,
            "max_attempts": old.max_attempts,
            "worker_id": old.worker_id,
            "last_error": old.last_error,
            "correlation_id": old.correlation_id,
            "available_at_ms": old.available_at_ms,
            "locked_at_ms": old.locked_at_ms,
            "heartbeat_at_ms": old.heartbeat_at_ms,
            "completed_at_ms": old.completed_at_ms,
            "created_at_ms": old.created_at_ms,
            "updated_at_ms": old.updated_at_ms,
        }
        payload.update(changes)
        record = ContinuationJobRecord(**payload)
        self._jobs[job_id] = record
        return record


def _spec(next_run_id: str = "run-next", max_attempts: int = 2) -> ContinuationJobSpec:
    return ContinuationJobSpec(
        user_request_id="request-1",
        project_id="project-1",
        previous_run_id="run-prev",
        next_run_id=next_run_id,
        max_attempts=max_attempts,
        correlation_id="corr-1",
    )


def test_continuation_queue_protocol_runtime_check():
    port: ContinuationQueuePort = _InMemoryContinuationQueue()

    assert isinstance(port, ContinuationQueuePort)


def test_continuation_job_record_validates_attempt_bounds():
    base = {
        "job_id": "job-1",
        "user_request_id": "request-1",
        "project_id": "project-1",
        "previous_run_id": "run-prev",
        "next_run_id": "run-next",
        "status": ContinuationJobStatus.QUEUED,
    }

    with pytest.raises(ValueError, match="attempts"):
        ContinuationJobRecord(**base, attempts=-1, max_attempts=1)

    with pytest.raises(ValueError, match="max_attempts"):
        ContinuationJobRecord(**base, attempts=0, max_attempts=0)

    with pytest.raises(ValueError, match="attempts"):
        ContinuationJobRecord(**base, attempts=2, max_attempts=1)


def test_continuation_queue_idempotent_enqueue_and_claim_order():
    queue = _InMemoryContinuationQueue()

    first = queue.enqueue_for_run(_spec("run-next-1"), job_id="job-1")
    replay = queue.enqueue_for_run(_spec("run-next-1"), job_id="job-ignored")
    second = queue.enqueue_for_run(_spec("run-next-2"), job_id="job-2")

    assert replay == first
    assert second.job_id == "job-2"

    claimed = queue.claim_next(worker_id="worker-1")
    assert claimed is not None
    assert claimed.job_id == "job-1"
    assert claimed.status == ContinuationJobStatus.RUNNING
    assert claimed.worker_id == "worker-1"


def test_continuation_queue_retry_and_dead_letter_lifecycle():
    queue = _InMemoryContinuationQueue()
    job = queue.enqueue_for_run(_spec(max_attempts=1))
    claimed = queue.claim_next(worker_id="worker-1")
    assert claimed is not None

    started = queue.mark_attempt_started(job.job_id)
    assert started is not None
    assert started.attempts == 1

    failed = queue.complete_failure(job.job_id, error="boom")
    assert failed is not None
    assert failed.status == ContinuationJobStatus.DEAD_LETTER
    assert failed.last_error == "boom"


def test_continuation_queue_reclaims_stale_running_jobs():
    queue = _InMemoryContinuationQueue()
    job = queue.enqueue_for_run(_spec())
    claimed = queue.claim_next(worker_id="worker-1", available_at_ms=2_000)
    assert claimed is not None
    assert queue.heartbeat(job.job_id, heartbeat_at_ms=1_000)

    assert queue.reclaim_stale(stale_before_ms=1_500) == 1

    reclaimed = queue.load_job(job.job_id)
    assert reclaimed is not None
    assert reclaimed.status == ContinuationJobStatus.QUEUED
    assert reclaimed.worker_id is None
