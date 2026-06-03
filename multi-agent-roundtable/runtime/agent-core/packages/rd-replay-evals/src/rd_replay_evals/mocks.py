"""replay 时的 mock LLM 与 mock Tool executor。

Codex 推荐边界：mock LLM stream + mock tool 返回值；persistence 用 memory；
workspace 用 ephemeral / mock。仅验证 engine transcript 行为。
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from rd_agent_contracts import AgentEvent

from .trace_format import GoldenTrace

_STREAM_EVENT_TYPES = {
    "text_delta",
    "thinking_delta",
    "tool_use",
    "usage",
    "message_start",
    "message_stop",
}


class MockLLMProvider:
    """按 trace 录制顺序重放 stream chunk。

    stream_chunks 本身是 async generator function（直接 async def + yield），
    使用方：`async for c in provider.stream_chunks(turn_id="...")`。
    """

    def __init__(self, trace: GoldenTrace) -> None:
        self._trace = trace

    async def stream_chunks(self, turn_id: str) -> AsyncIterator[AgentEvent]:
        for e in self._trace.events:
            if e.turn_id == turn_id and e.event_type in _STREAM_EVENT_TYPES:
                yield e


class MockToolExecutor:
    """按 tool_use_id 查录制结果，直接返回。

    若 tool_use_id 在 trace 中找不到 tool_completed event，抛 KeyError——
    这是 replay 信号：录制不完整或 engine 决策与录制不一致。
    """

    def __init__(self, trace: GoldenTrace) -> None:
        self._results: dict[str, dict[str, Any]] = {}
        for e in trace.events:
            if e.event_type == "tool_completed":
                tu_id = e.payload.get("tool_use_id")
                if tu_id:
                    self._results[tu_id] = e.payload

    async def execute(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input: dict[str, Any],
    ) -> dict[str, Any]:
        if tool_use_id not in self._results:
            raise KeyError(tool_use_id)
        return self._results[tool_use_id]
