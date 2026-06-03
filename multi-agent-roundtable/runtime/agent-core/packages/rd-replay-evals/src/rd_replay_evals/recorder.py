"""RecordingEventSink — 实现 EventSink port，把 emit 的 AgentEvent 收集起来，
最终通过 finalize_to_trace 输出为 GoldenTrace。

集成到 codesphere-saas 时，作为 SaasEventSink 的 fan-out 之一。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from rd_agent_contracts import AgentEvent

from .trace_format import GoldenTrace, TraceMeta


@dataclass
class RecordingEventSink:
    """结构上满足 EventSink Protocol（structural subtyping）。"""

    run_id: str
    _events: list[AgentEvent] = field(default_factory=list)

    async def emit(self, event: AgentEvent) -> None:
        if event.run_id != self.run_id:
            return
        self._events.append(event)


def finalize_to_trace(
    sink: RecordingEventSink,
    category: str,
    tags: list[str] | None = None,
    schema_version: str = "1.0.0",
) -> GoldenTrace:
    events = sorted(sink._events, key=lambda e: e.seq)
    meta = TraceMeta(
        trace_id=f"rec_{sink.run_id}",
        recorded_at_ms=events[0].timestamp_ms if events else 0,
        category=category,
        run_id=sink.run_id,
        schema_version=schema_version,
        tags=tags or ["recorder", "phase-a-week-2-3"],
    )
    return GoldenTrace(meta=meta, events=events)
