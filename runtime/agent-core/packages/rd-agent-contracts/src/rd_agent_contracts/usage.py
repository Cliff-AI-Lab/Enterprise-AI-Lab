"""Usage 容错模型。

Codex 风险点：provider usage chunk 可能缺失或为 0，逐 turn billing 会漏扣或误停。
本模块约定：缺失字段补 0，None 输入返回全零 Usage 占位。
billing 决策由 H2 Meter 自己处理（idempotency_key + 缺失策略），契约只保证字段齐。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def total(self) -> int:
        return self.input_tokens + self.output_tokens


def normalize_usage(raw: dict | None) -> Usage:
    """provider stream 末尾 usage chunk -> Usage。

    缺失字段补 0；raw=None 返回全零 Usage（不抛异常）。
    """
    if raw is None:
        return Usage()
    return Usage(
        input_tokens=int(raw.get("input_tokens", 0) or 0),
        output_tokens=int(raw.get("output_tokens", 0) or 0),
        cache_creation_input_tokens=int(raw.get("cache_creation_input_tokens", 0) or 0),
        cache_read_input_tokens=int(raw.get("cache_read_input_tokens", 0) or 0),
    )
