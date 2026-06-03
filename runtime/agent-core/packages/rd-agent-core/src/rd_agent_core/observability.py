"""Observer port for run-level metrics and tracing."""

from __future__ import annotations

import inspect
from typing import Protocol, runtime_checkable

from .summary import RunSummary


@runtime_checkable
class RunObserverPort(Protocol):
    def record_run_summary(self, summary: RunSummary) -> None: ...


@runtime_checkable
class AsyncRunObserverPort(Protocol):
    async def record_run_summary(self, summary: RunSummary) -> None: ...


RunObserverLike = RunObserverPort | AsyncRunObserverPort


async def notify_run_observer(
    observer: RunObserverLike | None,
    summary: RunSummary,
) -> Exception | None:
    if observer is None:
        return None
    try:
        result = observer.record_run_summary(summary)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # noqa: BLE001 - observability must not mutate run outcome.
        return exc
    return None
