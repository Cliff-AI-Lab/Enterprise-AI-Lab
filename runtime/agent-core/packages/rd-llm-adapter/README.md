# rd-llm-adapter

低层 LLM provider 适配器包：Transport / StreamParserSession 协议 + 具体 adapter 实现 + recorder。

## Hero use case

按约定实现一个 provider adapter（不通过继承——见下方"关于 Adapter 抽象"）：

```python
from rd_llm_adapter import StreamParserSession  # Protocol，仅做类型注解


class MyProviderAdapter:
    adapter_kind = "my_provider"

    def build_request(self, *, model, system_prompt, messages, tools, max_tokens, **provider_specific):
        # provider 协议特定的参数（reasoning_effort / thinking_budget_tokens / 等）
        # 由各 adapter 自己声明，不强求共通签名
        return {...}

    def create_parser_session(self, profile=None) -> StreamParserSession:
        return MyProviderParserSession(profile)


# 注册到 registry 后，调用方通过 adapter_kind 解析
from rd_llm_adapter.registry import resolve_adapter
adapter = resolve_adapter("my_provider")
```

## 关于 Adapter 抽象

本包**故意不**导出 `Adapter` Protocol。原因：现有 `OpenAICompatAdapter` / `AnthropicNativeAdapter`
的 `build_request` 签名因 provider 协议本身不同（OpenAI Responses 用 `reasoning_effort: low|medium|high`
字符串档；Anthropic Messages 用 `thinking.budget_tokens: int` 整数预算），没有共通最小公倍数可以
抽成 Protocol。

**Adapter 类型抽象**等 Phase B-3 engine extraction 后基于 `TurnRequest` 中间态契约定义。当前
`Transport` / `StreamParserSession` 已稳定可用——前者是 HTTP/SDK 调用层，后者是单 turn 流解析的
stateful session 契约。详见 [`base.py`](src/rd_llm_adapter/base.py) module docstring。

## 暴露符号

- 协议：`Transport` / `StreamParserSession`（adapter 通过约定实现，不通过继承）
- StandardEvent 9 类：`TextDelta` / `ReasoningDelta` / `ToolCallStart` / `ToolCallIdDelta` /
  `ToolCallNameDelta` / `ToolCallArgsDelta` / `ToolCallEnd` / `UsageUpdate` / `TurnDone`
- Capabilities：`ModelCapabilities` / `ProtocolLimits` / `ThinkingExtractionConfig`
- Adapter 具体类：`OpenAICompatAdapter` / `AnthropicNativeAdapter`
- Transport 具体类：`OpenAICompatTransport` / `AnthropicNativeTransport`
- Recorder：`StreamRecorder` / `RecordedTurn` / `ReplayEvents`
- Registry：`resolve_adapter` / `resolve_transport` / `resolve_adapter_for_profile` /
  `resolve_transport_for_profile` / `supported_adapter_kinds` / `supported_transport_kinds`

## 不暴露

- 具体 ParserSession 类（`*ParserSession`，是实现细节，通过 `adapter.create_parser_session()` 间接获取）
- `Adapter` Protocol（见上节，B-3 才设计）
- Channel router（rd-llm-gateway 2.0 职责）
- Provider lock 实施（rd-orchestration 职责）
- Retry 策略（rd-llm-gateway 2.0 职责）

## 设计文档

详见 [`docs/MODEL-ADAPTER.md`](../../docs/MODEL-ADAPTER.md)（v8 spec，2707 行）。

> ⚠️ MODEL-ADAPTER.md §5 的 `ModelAdapter` Protocol 定义自 Phase B-1 ship 起 stale
> （`build_request` 签名跟 shipped 具体类不一致）。该节标了 STALE 警告，新实现请按本 README
> 的 hero use case 模式来。

