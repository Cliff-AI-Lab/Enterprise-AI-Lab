"""StreamNormalizer —— 把任意 provider 的 chunk 流归一化为 StreamChunk。

设计要点（来自 Codex 两轮风险点）：
- normalizer 自己生成单调 seq，不信任 provider
- length 截断的 tool_call partial json 必须标 PARTIAL，绝不"修复"为 COMPLETE
- 非法 JSON 标 INVALID
- usage chunk 缺失时，给 zero Usage 占位
"""
from __future__ import annotations

from typing import Any

from rd_agent_contracts import ToolCallStatus, normalize_usage

from .types import StreamChunk, StreamChunkType


class StreamNormalizer:
    """有状态：维护 seq 计数器。每个 stream_chat 调用一个新实例。"""

    def __init__(self) -> None:
        self._seq = 0

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def message_start(
        self, raw: dict[str, Any] | None = None
    ) -> StreamChunk:
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.MESSAGE_START,
            raw=raw,
        )

    def text_delta(
        self, text: str, raw: dict[str, Any] | None = None
    ) -> StreamChunk:
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.TEXT_DELTA,
            text=text,
            raw=raw,
        )

    def thinking_delta(
        self, text: str, raw: dict[str, Any] | None = None
    ) -> StreamChunk:
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.THINKING_DELTA,
            text=text,
            raw=raw,
        )

    def tool_use_complete(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input_json: str,
        raw: dict[str, Any] | None = None,
    ) -> StreamChunk:
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.TOOL_USE,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input_partial=tool_input_json,
            tool_call_status=ToolCallStatus.COMPLETE,
            raw=raw,
        )

    def tool_use_partial(
        self,
        tool_use_id: str,
        tool_name: str,
        tool_input_partial_json: str,
        raw: dict[str, Any] | None = None,
    ) -> StreamChunk:
        """length 截断未闭合 —— P5 规则：不可执行。"""
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.TOOL_USE,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input_partial=tool_input_partial_json,
            tool_call_status=ToolCallStatus.PARTIAL,
            raw=raw,
        )

    def tool_use_invalid(
        self,
        tool_use_id: str,
        tool_name: str,
        raw: str,
        raw_chunk: dict[str, Any] | None = None,
    ) -> StreamChunk:
        """非法 JSON —— P5 规则：不可执行。"""
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.TOOL_USE,
            tool_use_id=tool_use_id,
            tool_name=tool_name,
            tool_input_partial=raw,
            tool_call_status=ToolCallStatus.INVALID,
            raw=raw_chunk,
        )

    def usage(self, raw_usage: dict[str, Any] | None) -> StreamChunk:
        """usage chunk 缺失也返回 zero Usage chunk，保持 seq 序列完整。"""
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.USAGE,
            usage=normalize_usage(raw_usage),
            raw=raw_usage if isinstance(raw_usage, dict) else None,
        )

    def message_stop(
        self, raw: dict[str, Any] | None = None
    ) -> StreamChunk:
        return StreamChunk(
            seq=self._next_seq(),
            chunk_type=StreamChunkType.MESSAGE_STOP,
            raw=raw,
        )
