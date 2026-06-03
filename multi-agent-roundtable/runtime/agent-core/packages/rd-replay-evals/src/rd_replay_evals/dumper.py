"""第 1 周快通法：从 codesphere-saas events 表 dump 出 GoldenTrace。

input: 一组 EventRow（来自 SQLAlchemy 查询）；
output: GoldenTrace（按 seq 排序、做 schema 翻译）。

Phase A 第 2-3 周会写专门 recorder 替代此 dumper。
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from rd_agent_contracts import AgentEvent

from .trace_format import GoldenTrace, TraceMeta


@dataclass(frozen=True)
class EventRow:
    """对应 codesphere-saas app.models.events.Event 的简化形态。"""

    project_id: str
    event_type: str
    content_json: str
    created_at_ms: int


def dump_event_rows(
    rows: list[EventRow],
    run_id: str,
    category: str,
    schema_version: str = "1.0.0",
    tags: list[str] | None = None,
) -> GoldenTrace:
    events: list[AgentEvent] = []
    for row in rows:
        if row.event_type != "ai_session":
            continue
        try:
            content = json.loads(row.content_json)
        except json.JSONDecodeError:
            continue
        data = (content or {}).get("data") or {}
        if data.get("run_id") != run_id:
            continue
        events.append(
            AgentEvent(
                seq=int(data.get("seq", 0)),
                timestamp_ms=int(
                    data.get("timestamp_ms", row.created_at_ms)
                ),
                run_id=run_id,
                turn_id=str(data.get("turn_id", "unknown")),
                event_type=str(
                    content.get("type")
                    or data.get("event")
                    or "unknown"
                ),
                payload=data.get("payload") or {},
                schema_version=schema_version,
            )
        )

    events.sort(key=lambda e: e.seq)

    meta = TraceMeta(
        trace_id=f"dump_{run_id}",
        recorded_at_ms=events[0].timestamp_ms if events else 0,
        category=category,
        run_id=run_id,
        schema_version=schema_version,
        tags=tags or ["dumper", "phase-a-week-1"],
    )
    return GoldenTrace(meta=meta, events=events)
