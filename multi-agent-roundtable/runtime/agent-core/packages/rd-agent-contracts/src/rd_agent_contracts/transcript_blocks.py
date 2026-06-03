"""Typed transcript content blocks（contracts 1.2，跟 model_adapter v8 字段对齐）。

字段定义跟随 codesphere-saas/app/services/agent_runner/model_adapter/messages.py
（已经 Codex 6 轮 review 的真实实现），让 rd-llm-adapter 移植时
messages.py 可纯 re-export，避免双源定义。

使用方：
- rd-llm-adapter 的 TurnDone.content 用这些类型
- rd-agent-core engine 的 transcript invariants 用这些类型
- saas-adapter 持久化时 byte-equal 保留 ReasoningBlock.signature / .data

ReasoningBlock 是 Anthropic native thinking 的 first-class 表达：
- 普通 thinking：text + signature
- redacted_thinking：data（加密 blob）+ redacted=True
- DeepSeek/Kimi/GLM reasoning_content：text + signature=None + redacted=False

ProviderState 是 unstructured dict，让 adapter 透明传递 provider-specific
状态（如 Anthropic 的 stop_sequence 上下文），engine 不解析。

每个 dataclass 含 type discriminator 字段（"text" / "reasoning" / "tool_use" /
"invalid_tool_call"），便于 JSON serialize / replay fixture 解析。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TextBlock:
    """普通文本 block。"""
    text: str
    type: str = "text"
    provider_data: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReasoningBlock:
    """思维链 block。Anthropic thinking / redacted_thinking 的 first-class 表达。

    - 普通 thinking：text + signature（必须保留以支持 multi-turn）
    - redacted_thinking：data（provider 原始加密 blob 字符串）+ redacted=True
    - DeepSeek/Kimi/GLM 的 reasoning_content：text + signature=None + redacted=False
    """
    text: str = ""
    type: str = "reasoning"
    signature: str | None = None  # Anthropic native thinking 的 block 签名
    redacted: bool = False
    data: str | None = None  # Anthropic redacted_thinking 的加密 blob
    provider_data: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.redacted and not self.data:
            raise ValueError("redacted reasoning block requires data")
        if self.data is not None and not self.redacted:
            raise ValueError("reasoning block data is only valid when redacted=True")


@dataclass(frozen=True)
class ToolUseBlock:
    """LLM 发起的工具调用（complete 状态）。"""
    id: str
    name: str
    input: dict[str, Any] = field(default_factory=dict)
    type: str = "tool_use"


@dataclass(frozen=True)
class InvalidToolCall:
    """解析失败的 tool_call（partial JSON / 格式错误等）。

    P5 engine 永不执行 InvalidToolCall。保留这个类型让 adapter 能精确
    报告"模型试图调工具但参数解析失败"，跟"complete tool call"区分开。
    """
    id: str
    name: str
    raw_args: str
    parse_error: str
    index: int
    encoding: str | None = None
    type: str = "invalid_tool_call"


@dataclass(frozen=True)
class StandardToolCall:
    """完整工具调用规范化形态（含 encoding 标注）。

    跟 ToolUseBlock 的差异：StandardToolCall 是 adapter 已确认 complete
    的 tool call（可执行），ToolUseBlock 是 transcript 表达层的 content block。
    encoding 字段记录上游 provider 的编码方式（native_json / xml / etc）。
    """
    id: str
    name: str
    input: dict[str, Any]
    encoding: str = "native_json"


@dataclass(frozen=True)
class ProviderState:
    """Provider-specific 状态（透明 dict）。

    让 adapter 把 provider 返回的额外字段（stop_sequence、cache 信息、
    content filter 决策等）原样透传给 engine，engine 不解析、persistence
    透明保留 byte-equal。
    """
    data: dict[str, Any] = field(default_factory=dict)


# Type alias：Message.content 可以是 str（旧形态）或 list[StandardContentBlock]（v1.1+）
StandardContentBlock = TextBlock | ReasoningBlock | ToolUseBlock | InvalidToolCall
