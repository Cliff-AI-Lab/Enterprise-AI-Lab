"""ChatRequest / StreamChunk — gateway 与 engine 之间的接口。

StreamChunk 是 normalizer 的输出，已经屏蔽 Anthropic / OpenAI 的差异。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from rd_agent_contracts import ToolCallStatus, Usage


@dataclass(frozen=True)
class ChatRequest:
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 1.0
    system: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class StreamChunkType(StrEnum):
    TEXT_DELTA = "text_delta"
    TOOL_USE = "tool_use"
    THINKING_DELTA = "thinking_delta"
    MESSAGE_START = "message_start"
    MESSAGE_STOP = "message_stop"
    USAGE = "usage"


@dataclass(frozen=True)
class StreamChunk:
    """Normalizer 输出的 chunk。

    强约束：seq >= 1 单调递增；tool_call_status 由 normalizer 显式标注。
    """

    seq: int
    chunk_type: StreamChunkType
    text: str | None = None
    tool_use_id: str | None = None
    tool_name: str | None = None
    tool_input_partial: str | None = None
    tool_call_status: ToolCallStatus | None = None
    usage: Usage | None = None
    raw: dict[str, Any] | None = None  # 原 provider chunk，用于 replay

    def __post_init__(self) -> None:
        if self.seq < 1:
            raise ValueError(f"seq must be >= 1, got {self.seq}")
