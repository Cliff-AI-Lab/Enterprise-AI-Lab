"""LLM Usage 标准化模块（adapter 内部使用）。

将各 LLM provider 返回的不同格式的 token 用量统一归一化为 UsageRecord。
所有 provider 边界（adapter、client）在拿到原始 usage 后必须调用 normalize_usage()，
之后全链路只使用 UsageRecord 或其 to_dict() 输出。

已知 provider 字段映射：
- Anthropic: input_tokens, output_tokens（原生标准）
- OpenAI:    prompt_tokens, completion_tokens, total_tokens
- Gemini:    prompt_token_count, candidates_token_count
- Kimi/DeepSeek (Sub2API): OpenAI 兼容格式

注：B-1 Phase 把 codesphere-saas/app/services/llm_usage.py inline 进 rd-llm-adapter
包内私有模块，避免对宿主项目的反向依赖（spec §5.5 single source）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("rd_llm_adapter.usage")

# 已知 provider 别名 → 标准字段
_ALIASES: dict[str, str] = {
    "prompt_tokens": "input_tokens",
    "completion_tokens": "output_tokens",
    "prompt_token_count": "input_tokens",
    "candidates_token_count": "output_tokens",
    "cached_input_tokens": "cache_read_input_tokens",
    "cache_read_input_tokens": "cache_read_input_tokens",
    "cache_creation_input_tokens": "cache_creation_input_tokens",
}

_TOP_LEVEL_USAGE_KEYS = tuple(
    sorted(
        {
            *_ALIASES.keys(),
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cached_input_tokens",
            "cache_read_input_tokens",
            "cache_creation_input_tokens",
            "reasoning_tokens",
            "prompt_tokens_details",
            "completion_tokens_details",
            "input_tokens_details",
            "output_tokens_details",
        }
    )
)

_CACHE_READ_INPUT_DETAIL_KEYS = (
    "cached_tokens",
    "cache_read_tokens",
    "cache_read_input_tokens",
)

_CACHE_CREATION_INPUT_DETAIL_KEYS = (
    "cache_creation_input_tokens",
)

_REASONING_DETAIL_KEYS = ("reasoning_tokens",)


@dataclass(frozen=True)
class UsageRecord:
    """标准化的 token 用量记录"""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0

    def __post_init__(self) -> None:
        read_tokens = self.cache_read_input_tokens
        creation_tokens = self.cache_creation_input_tokens
        if self.cached_input_tokens and not (read_tokens or creation_tokens):
            read_tokens = self.cached_input_tokens
            object.__setattr__(self, "cache_read_input_tokens", read_tokens)
        derived_cached_tokens = read_tokens + creation_tokens
        if self.cached_input_tokens != derived_cached_tokens:
            object.__setattr__(self, "cached_input_tokens", derived_cached_tokens)

    def to_dict(self) -> dict[str, int]:
        payload = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens or (self.input_tokens + self.output_tokens),
        }
        if self.cache_read_input_tokens:
            payload["cache_read_input_tokens"] = self.cache_read_input_tokens
        if self.cache_creation_input_tokens:
            payload["cache_creation_input_tokens"] = self.cache_creation_input_tokens
        if self.cached_input_tokens:
            payload["cached_input_tokens"] = self.cached_input_tokens
        if self.reasoning_tokens:
            payload["reasoning_tokens"] = self.reasoning_tokens
        return payload

    def __add__(self, other: UsageRecord) -> UsageRecord:
        return UsageRecord(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            total_tokens=(
                self.input_tokens
                + other.input_tokens
                + self.output_tokens
                + other.output_tokens
            ),
            cache_read_input_tokens=(
                self.cache_read_input_tokens + other.cache_read_input_tokens
            ),
            cache_creation_input_tokens=(
                self.cache_creation_input_tokens + other.cache_creation_input_tokens
            ),
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


def normalize_usage(raw: Any) -> UsageRecord:
    """将任意 provider 返回的 usage（dict 或 SDK 对象）归一化为 UsageRecord。"""
    if not raw:
        return UsageRecord()

    # SDK 对象转 dict
    if not isinstance(raw, dict):
        raw_dict: dict[str, Any] = {}
        for key in _TOP_LEVEL_USAGE_KEYS:
            val = getattr(raw, key, None)
            if val is not None:
                raw_dict[key] = val
        raw = raw_dict

    has_split_cache_fields = (
        "cache_read_input_tokens" in raw or "cache_creation_input_tokens" in raw
    )

    # 映射别名到标准字段并累加。拆分 cache 字段优先；legacy
    # cached_input_tokens 只在没有拆分字段时作为 read-cache 兼容输入。
    mapped: dict[str, int] = {}
    for key, value in raw.items():
        if key == "cached_input_tokens" and has_split_cache_fields:
            continue
        value_int = _int_or_none(value)
        if value_int is None:
            continue
        canonical = _ALIASES.get(key, key)
        mapped[canonical] = mapped.get(canonical, 0) + value_int

    cache_read_input_tokens = mapped.get("cache_read_input_tokens", 0)
    cache_creation_input_tokens = mapped.get("cache_creation_input_tokens", 0)
    reasoning_tokens = mapped.get("reasoning_tokens", 0)
    for detail_key in ("prompt_tokens_details", "input_tokens_details"):
        detail = raw.get(detail_key)
        cache_read_input_tokens += _sum_detail_values(
            detail,
            _CACHE_READ_INPUT_DETAIL_KEYS,
        )
        cache_creation_input_tokens += _sum_detail_values(
            detail,
            _CACHE_CREATION_INPUT_DETAIL_KEYS,
        )
    for detail_key in ("completion_tokens_details", "output_tokens_details"):
        detail = raw.get(detail_key)
        reasoning_tokens += _sum_detail_values(detail, _REASONING_DETAIL_KEYS)

    inp = mapped.get("input_tokens", 0)
    out = mapped.get("output_tokens", 0)
    total = mapped.get("total_tokens", 0) or (inp + out)

    if (
        inp == 0
        and out == 0
        and cache_read_input_tokens == 0
        and cache_creation_input_tokens == 0
        and reasoning_tokens == 0
        and raw
    ):
        logger.warning(
            "Usage normalization got zero tokens from non-empty raw data: keys=%s",
            list(raw.keys()) if isinstance(raw, dict) else type(raw).__name__,
        )

    return UsageRecord(
        input_tokens=inp,
        output_tokens=out,
        total_tokens=total,
        cache_read_input_tokens=cache_read_input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        reasoning_tokens=reasoning_tokens,
    )


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _sum_detail_values(detail: Any, keys: tuple[str, ...]) -> int:
    if not detail:
        return 0
    total = 0
    for key in keys:
        if isinstance(detail, dict):
            value = detail.get(key)
        else:
            value = getattr(detail, key, None)
        value_int = _int_or_none(value)
        if value_int is not None:
            total += value_int
    return total
