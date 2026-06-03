"""LLMProvider port —— 所有 adapter 都实现此接口。"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from .types import ChatRequest, StreamChunk


@runtime_checkable
class LLMProvider(Protocol):
    async def stream_chat(
        self, req: ChatRequest
    ) -> AsyncIterator[StreamChunk]: ...
