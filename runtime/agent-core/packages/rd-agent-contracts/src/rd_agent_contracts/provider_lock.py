"""ProviderLock — 防 model A/B 路由跨 transcript 换 provider。

字段在 P1，决策与持久化在 P8，强制读取在 P5，路由实施在 P2。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderLock:
    provider_id: str
    adapter_family: str  # anthropic | openai_compat | gemini | ...
    tool_protocol: str  # anthropic_tool_use | openai_tool_calls | ...
    reasoning_protocol: str | None
    locked_at_run_id: str

    def is_compatible_with(
        self,
        adapter_family: str,
        tool_protocol: str,
        reasoning_protocol: str | None = None,
    ) -> bool:
        return (
            self.adapter_family == adapter_family
            and self.tool_protocol == tool_protocol
            and self.reasoning_protocol == reasoning_protocol
        )
