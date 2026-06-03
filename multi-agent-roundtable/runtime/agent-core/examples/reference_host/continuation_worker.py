"""Reference continuation worker built on the public queue contract."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from rd_agent_contracts import ContinuationJobRecord, ContinuationQueuePort

ContinuationJobHandler = Callable[
    [ContinuationJobRecord],
    None | ContinuationJobRecord | Awaitable[None | ContinuationJobRecord],
]


@dataclass
class ReferenceContinuationWorker:
    queue: ContinuationQueuePort
    worker_id: str
    handler: ContinuationJobHandler

    async def run_once(self) -> ContinuationJobRecord | None:
        claimed = self.queue.claim_next(worker_id=self.worker_id)
        if claimed is None:
            return None

        job = self.queue.mark_attempt_started(claimed.job_id) or claimed
        try:
            result = self.handler(job)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:  # noqa: BLE001 - worker boundary records failure state.
            return self.queue.complete_failure(job.job_id, error=str(exc))
        return self.queue.complete_success(job.job_id)
