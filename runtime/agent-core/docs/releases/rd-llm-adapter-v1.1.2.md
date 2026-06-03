# rd-llm-adapter v1.1.2

## 变更

- 发布 `py.typed` 类型标记，让下游 host 和 `rd-agent-core` 在类型检查中获得包级 typed 支持。

## 兼容性

- 无 parser、transport 或标准事件语义变更。
- 依赖 `rd-agent-contracts>=1.14.1,<2.0.0`。
