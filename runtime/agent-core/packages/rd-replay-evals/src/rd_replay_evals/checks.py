"""5 条 replay 通过条件的独立检查器。

按设计文档 §6.1 Phase A 验证标准：
1. normalized event 序列一致
2. tool_call 执行集合一致
3. 最终 transcript hash 一致
4. stop_reason 一致
5. usage 容错规则一致
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from rd_agent_contracts import AgentEvent, StopReason, Usage


class ReplayMismatch(AssertionError):  # noqa: N818
    """replay 不一致。"""


def check_event_sequence_match(
    expected: list[AgentEvent],
    actual: list[AgentEvent],
) -> None:
    if len(expected) != len(actual):
        raise ReplayMismatch(
            f"event count mismatch: "
            f"expected={len(expected)} actual={len(actual)}"
        )
    for e, a in zip(expected, actual, strict=True):
        if (e.seq, e.event_type, e.payload) != (
            a.seq,
            a.event_type,
            a.payload,
        ):
            raise ReplayMismatch(
                f"event mismatch at seq={e.seq}: "
                f"expected={e.event_type}/{e.payload}, "
                f"actual={a.event_type}/{a.payload}"
            )


def check_tool_call_set_match(
    expected: list[AgentEvent],
    actual: list[AgentEvent],
) -> None:
    expected_set = {
        e.payload.get("tool_use_id")
        for e in expected
        if e.event_type == "tool_use"
    }
    actual_set = {
        a.payload.get("tool_use_id")
        for a in actual
        if a.event_type == "tool_use"
    }
    if expected_set != actual_set:
        raise ReplayMismatch(
            f"tool_call set mismatch: "
            f"expected={expected_set} actual={actual_set}"
        )


def check_transcript_hash_match(
    expected: list[AgentEvent],
    actual: list[AgentEvent],
) -> None:
    h_e = _hash_events(expected)
    h_a = _hash_events(actual)
    if h_e != h_a:
        raise ReplayMismatch(
            f"transcript hash mismatch: expected={h_e} actual={h_a}"
        )


def _hash_events(events: list[AgentEvent]) -> str:
    blob = json.dumps(
        [asdict(e) for e in events],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def check_stop_reason_match(
    expected: StopReason,
    actual: StopReason,
) -> None:
    if expected != actual:
        raise ReplayMismatch(
            f"stop_reason mismatch: expected={expected} actual={actual}"
        )


def check_usage_match(expected: Usage, actual: Usage) -> None:
    if expected != actual:
        raise ReplayMismatch(
            f"usage mismatch: expected={expected} actual={actual}"
        )
