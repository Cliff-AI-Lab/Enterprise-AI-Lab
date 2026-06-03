"""Golden trace 文件格式（jsonl）+ 写读 round-trip + 单调 seq 校验。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import IO, Any

from rd_agent_contracts import AgentEvent


@dataclass(frozen=True)
class TraceMeta:
    trace_id: str
    recorded_at_ms: int
    category: str
    run_id: str
    schema_version: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class GoldenTrace:
    meta: TraceMeta
    events: list[AgentEvent]

    def __post_init__(self) -> None:
        seqs = [e.seq for e in self.events]
        if seqs != sorted(seqs):
            raise ValueError(f"events seq must be monotonic; got {seqs}")


def write_trace(trace: GoldenTrace, fp: IO[str]) -> None:
    """jsonl 格式：第一行 meta，后续每行一个 event。"""
    meta_line = json.dumps(
        {"_kind": "meta", **trace.meta.__dict__}, ensure_ascii=False
    )
    fp.write(meta_line + "\n")
    for e in trace.events:
        event_line = json.dumps(
            {"_kind": "event", **e.to_dict()}, ensure_ascii=False
        )
        fp.write(event_line + "\n")


def read_trace(fp: IO[str]) -> GoldenTrace:
    meta: TraceMeta | None = None
    events: list[AgentEvent] = []
    for raw_line in fp:
        stripped = raw_line.strip()
        if not stripped:
            continue
        obj: dict[str, Any] = json.loads(stripped)
        kind = obj.pop("_kind")
        if kind == "meta":
            meta = TraceMeta(**obj)
        elif kind == "event":
            events.append(AgentEvent(**obj))
    if meta is None:
        raise ValueError("trace file missing meta line")
    return GoldenTrace(meta=meta, events=events)
