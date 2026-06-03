"""Re-export typed transcript blocks from rd-agent-contracts 1.2。

contracts 1.2 字段对齐了 model_adapter v8 实现，让本文件可以纯
re-export 而非保留本地定义——单一来源（spec §5.5），避免 contracts
和 rd-llm-adapter 双源 drift。

Phase B-3（rd-agent-core engine 抽出）和 saas-adapter 持久化
都直接用 contracts 这套类型，无需通过本 re-export 层。
"""
from rd_agent_contracts import (
    InvalidToolCall,
    ProviderState,
    ReasoningBlock,
    StandardContentBlock,
    StandardToolCall,
    TextBlock,
    ToolUseBlock,
)

__all__ = [
    "InvalidToolCall",
    "ProviderState",
    "ReasoningBlock",
    "StandardContentBlock",
    "StandardToolCall",
    "TextBlock",
    "ToolUseBlock",
]
