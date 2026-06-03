"""Host-neutral continuation queue contracts.

Continuation jobs connect a completed continuable run to the next bounded run.
The contract is intentionally ORM-free: hosts can back it with SQL, Redis, or a
managed queue while exposing the same lifecycle to the runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable


class ContinuationJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class ContinuationJobSpec:
    user_request_id: str
    project_id: str
    previous_run_id: str
    next_run_id: str
    max_attempts: int = 1
    correlation_id: str | None = None
    available_at_ms: int | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")


@dataclass(frozen=True)
class ContinuationJobRecord:
    """Observable continuation job state.

    ``attempts`` counts started execution attempts, incremented when a worker
    begins processing through ``mark_attempt_started``.
    """

    job_id: str
    user_request_id: str
    project_id: str
    previous_run_id: str
    next_run_id: str
    status: str
    attempts: int
    max_attempts: int
    worker_id: str | None = None
    last_error: str | None = None
    correlation_id: str | None = None
    available_at_ms: int | None = None
    locked_at_ms: int | None = None
    heartbeat_at_ms: int | None = None
    completed_at_ms: int | None = None
    created_at_ms: int | None = None
    updated_at_ms: int | None = None

    def __post_init__(self) -> None:
        if self.attempts < 0:
            raise ValueError("attempts must be >= 0")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.attempts > self.max_attempts:
            raise ValueError("attempts must be <= max_attempts")


@runtime_checkable
class ContinuationQueuePort(Protocol):
    """Persistence boundary for automatic AgentRun continuations.

    Implementations may own transactions or let callers do so. The protocol
    only defines observable queue state and transition semantics.
    """

    def enqueue_for_run(
        self,
        spec: ContinuationJobSpec,
        *,
        job_id: str | None = None,
    ) -> ContinuationJobRecord: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def mark_attempt_started(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def heartbeat(
        self,
        job_id: str,
        *,
        heartbeat_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def complete_success(
        self,
        job_id: str,
        *,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def complete_failure(
        self,
        job_id: str,
        *,
        error: str,
        retry_available_at_ms: int | None = None,
        completed_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def release_for_retry(
        self,
        job_id: str,
        *,
        error: str,
        available_at_ms: int | None = None,
    ) -> ContinuationJobRecord | None: ...

    def reclaim_stale(
        self,
        *,
        stale_before_ms: int,
    ) -> int: ...

    def load_job(self, job_id: str) -> ContinuationJobRecord | None: ...
