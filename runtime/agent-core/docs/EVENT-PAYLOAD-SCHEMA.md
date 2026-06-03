# Core Event Payload Schema

`rd-agent-core` 通过 `EventLogPort` 写入 `AgentEvent`。每个事件都有统一 envelope：

```python
AgentEvent(
    seq: int,
    timestamp_ms: int,
    run_id: str,
    turn_id: str,
    event_type: str,
    payload: dict[str, Any],
    schema_version: str,
    message_id: str | None = None,
    action_id: str | None = None,
)
```

本文档描述 core 当前写入的 `payload` 字段。字段是 JSON-compatible；host 可以额外派生 UI/billing/audit 投影，但不要改变原始 event log。

## Event Types

| Event Type | Payload Fields | Notes |
| --- | --- | --- |
| `turn_started` | `model: str \| None`, `turn_index: int`, `metadata: dict` | 每个 turn 开始时写入。 |
| `text_delta` | `text: str`, `block_index: int` | 模型普通文本增量。 |
| `reasoning_delta` | `text: str`, `block_index: int`, `provider_data: dict \| None` | 模型 reasoning/thinking 增量。 |
| `tool_call_started` | `index: int`, `call_id: str \| None`, `name: str \| None`, `encoding_hint: str \| None` | 工具调用 lifecycle 开始。 |
| `tool_call_delta` | `index: int` plus one of `call_id`, `name_delta`, `delta`; optional `call_id` | 工具 id/name/args 增量。 |
| `tool_call_completed` | `call_id: str`, `name: str`, `index: int`, `encoding: str`, `raw_args: str`, `parsed_input: dict \| None`, `parse_error: str \| None` | 工具调用参数流结束。`parse_error` 非空时不会执行。 |
| `tool_call_invalid` | `id: str`, `name: str`, `raw_args: str`, `parse_error: str`, `index: int`, `encoding: str \| None`, `type: "invalid_tool_call"` | 解析失败的工具调用，永不执行。 |
| `usage_update` | `input_tokens: int`, `output_tokens: int`, `total_tokens: int`, optional cache/reasoning fields, `usage_sequence: int` | `usage_sequence` 是同一 turn 内的 usage update 顺序。 |
| `tool_started` | `tool_name: str`, `tool_use_id: str` | core 准备执行工具时写入。被 safety policy 拒绝的工具也会先写 started。 |
| `tool_completed` | `tool_name: str`, `tool_use_id: str`, `result: ToolExecutionResult dict` | 工具执行成功。 |
| `tool_failed` | `tool_name: str`, `tool_use_id: str`, `result: ToolExecutionResult dict` | 工具执行失败、被 policy 拒绝、未声明、executor 缺失或 pause 后跳过。 |
| `turn_paused` | `tool_name: str`, `tool_use_id: str`, `stop_reason: str` | pause tool 成功执行后写入。 |
| `turn_completed` | `stop_reason: str`, `raw_stop_reason: str`, `tool_calls_executed: int`, `invalid_tool_calls: int`, `pause_requested: bool`, `terminal_text: str`, `terminal_reasoning: str`, `usage: Usage dict` | turn 终态汇总。 |

## ToolExecutionResult Dict

`tool_completed` 和 `tool_failed` 的 `result` 字段来自：

```python
ToolExecutionResult(
    ok: bool,
    content: str,
    error: dict[str, Any] | None = None,
    duration_ms: int | None = None,
    metadata: dict[str, Any] = {},
)
```

常见 `error.type`：

- `tool_not_declared`
- `tool_executor_missing`
- `tool_blocked`
- `tool_not_allowed`
- `tool_confirmation_required`
- `tool_skipped_after_pause`
- `max_tool_calls`
- `repeated_tool_call`
- 工具边界抛出的异常类名

## Compatibility Rules

- `event_type` 是 UI、billing、audit、replay 的主分派字段；
- `payload` 可以增加新字段，但不应删除已有字段；
- host 应容忍未知字段；
- `tool_failed.result.error.type` 应被视为机器可读错误分类；
- replay 和 billing 应以原始 `AgentEvent` 为准，而不是 UI 派生对象。

