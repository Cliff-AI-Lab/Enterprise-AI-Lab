"""Public low-level protocols for rd-llm-adapter.

包含两个稳定 Protocol：
- StreamParserSession：单 turn 流解析的 stateful session 契约
- Transport：HTTP/SDK 调用层契约

**关于 Adapter Protocol**：本模块**故意不**定义 `Adapter` Protocol。OpenAICompatAdapter
和 AnthropicNativeAdapter 的 `build_request` 签名因 provider 协议本身不同（OpenAI 的
`reasoning_effort: low|medium|high` 字符串档 vs Anthropic 的 `thinking.budget_tokens: int`
整数预算），没有共通最小公倍数可以抽成 Protocol。

Adapter 类型抽象等 Phase B-3 engine extraction 后，基于 `TurnRequest` 中间态契约设计。
当前调用方应依赖具体 adapter 类（OpenAICompatAdapter / AnthropicNativeAdapter）+
`adapter_kind` ClassVar 做识别，或通过 registry 函数 `resolve_adapter(kind)` 拿实例。
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable
from typing import Any, Protocol

from .events import StandardEvent


class StreamParserSession(Protocol):
    def feed(self, raw_chunk: Any) -> Iterable[StandardEvent]: ...

    def finalize(self) -> Iterable[StandardEvent]: ...

    def finalize_on_error(self) -> Iterable[StandardEvent]: ...


class Transport(Protocol):
    async def stream(
        self,
        request_body: dict[str, Any],
        *,
        api_key: str,
        base_url: str,
        timeout: float,
        extra_headers: dict[str, str] | None = None,
    ) -> AsyncIterator[Any]: ...
