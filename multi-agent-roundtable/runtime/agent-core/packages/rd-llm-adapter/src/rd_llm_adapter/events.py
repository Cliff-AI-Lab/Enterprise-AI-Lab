"""StandardEvent 9 类的数据契约。

**ToolCall 事件 lifecycle 约束**（B-1 ship 后明确）：

调用方在一个 turn 中按以下顺序消费 ToolCall 事件：

1. `ToolCallStart(index, call_id?, name?, encoding_hint?)` — 一个 tool call 开启
   - 已知 call_id/name 时 adapter 应在 ToolCallStart 中带上，避免后续 *Delta 重复发
   - 未知时 adapter 留空，等后续 *IdDelta / *NameDelta 增量补
2. 0 或多个 `ToolCallIdDelta` / `ToolCallNameDelta` / `ToolCallArgsDelta` — 增量元信息
   - **目标约束**（rd-llm-adapter 1.0.1 起声明，B-3 收紧）：*Delta 仅在对应字段在 ToolCallStart
     时未知（None）时才应发出
   - **当前现状**：OpenAICompatAdapter 在 ToolCallStart 已给 call_id 时仍可能发出
     ToolCallIdDelta（见 openai_compat.py:285-287）。这是已知冗余，消费方应对此容忍。
     B-3 抽 engine 时通过 TurnRequest 抽象统一收紧
3. `ToolCallEnd(call_id, name, index, encoding, raw_args, parsed_input, parse_error)`
   — tool call 结束

**ToolCallEnd 字段冗余说明**：`raw_args` / `parsed_input` / `parse_error` 与 TurnDone.content 中
最终的 ToolUseBlock / InvalidToolCall 字段重叠（同一信息的两个表达）。当前为了流式消费方便保留双
重表达；B-3 抽 engine 时统一让 TurnDone.content 作为唯一 truth，*Delta 仅承担流式 lifecycle 信号。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextDelta:
    text: str
    block_index: int = 0


@dataclass(frozen=True)
class ReasoningDelta:
    text: str
    block_index: int = 0
    provider_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class ToolCallStart:
    """Tool call lifecycle 起始事件。call_id/name 已知时应在此事件带上，
    避免后续 *IdDelta / *NameDelta 发出重复信息。详见模块 docstring。"""

    index: int
    call_id: str | None = None
    name: str | None = None
    encoding_hint: str | None = None


@dataclass(frozen=True)
class ToolCallIdDelta:
    index: int
    call_id: str


@dataclass(frozen=True)
class ToolCallNameDelta:
    index: int
    name_delta: str
    call_id: str | None = None


@dataclass(frozen=True)
class ToolCallArgsDelta:
    index: int
    delta: str
    call_id: str | None = None


@dataclass(frozen=True)
class ToolCallEnd:
    """Tool call lifecycle 结束事件。

    raw_args / parsed_input / parse_error 与 TurnDone.content 终态 ToolUseBlock /
    InvalidToolCall 字段冗余（同一信息双重表达）；当前保留为流式消费方便，B-3 收紧。
    """

    call_id: str
    name: str
    index: int
    encoding: str
    raw_args: str
    parsed_input: dict[str, Any] | None
    parse_error: str | None


@dataclass(frozen=True)
class UsageUpdate:
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
        total = self.total_tokens or (self.input_tokens + self.output_tokens)
        payload = {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": total,
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


@dataclass(frozen=True)
class TurnDone:
    """Turn 完成的终态聚合。

    `content` 是有序的 transcript truth（TextBlock / ReasoningBlock / ToolUseBlock /
    InvalidToolCall 按 provider 实际产出顺序排列）。

    `text_blocks` / `reasoning_blocks` / `tool_calls` / `invalid_tool_calls` 是 `content`
    的 **derived 视图**（按类型过滤的快捷访问），不是独立 truth。两者不一致时以 `content`
    为准。当前为流式/历史消费方便保留独立字段，**新代码应优先消费 `content`**；B-3 抽 engine
    时这些 derived 字段会移除或改 property。

    测试合约（rd-llm-adapter 1.0.1+ 强制）：所有 adapter emit 的 TurnDone，derived 字段必须
    可由 content 通过简单过滤完整重建——见 `tests/test_turn_done_derived_consistency.py`。
    """

    stop_reason: str
    content: list[Any]
    text_blocks: list[Any]
    reasoning_blocks: list[Any]
    tool_calls: list[Any]
    invalid_tool_calls: list[Any]
    sources: list[Any] = field(default_factory=list)
    usage: UsageUpdate | None = None
    provider_state: Any | None = None
    raw_stop_reason: str = ""


StandardEvent = (
    TextDelta
    | ReasoningDelta
    | ToolCallStart
    | ToolCallIdDelta
    | ToolCallNameDelta
    | ToolCallArgsDelta
    | ToolCallEnd
    | UsageUpdate
    | TurnDone
)
