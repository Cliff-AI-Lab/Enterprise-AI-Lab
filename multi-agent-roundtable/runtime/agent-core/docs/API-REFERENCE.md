# SDK API Reference

这份文档记录当前对外建议使用的 SDK 接口。更底层、未在此列出的函数或类可以在测试和内部实现中使用，但不建议接入方依赖。

## 包结构

| Package | 当前版本 | 用途 |
| --- | --- | --- |
| `rd-agent-contracts` | `1.14.1` | 数据结构、运行合同、host ports、`py.typed` |
| `rd-llm-adapter` | `1.1.2` | Provider 请求构造、流式 chunk 解析、标准事件、`py.typed` |
| `rd-agent-core` | `0.1.3` | Turn/Run kernel、AgentRunner、provider LLM client、事件写入、运行策略、取消、运行摘要/观测、conformance、业务 adapter 边界、testing harness |

## rd-agent-core

公开主路径索引：

- `AgentRunner`
- `AgentRunnerRequest`
- `AgentRunnerResult`
- `RunKernel`
- `RunRequest`
- `RunSummary`
- `RunObserverPort`
- `TurnKernel`
- `TurnRequest`
- `ToolSafetyPolicy`
- `CoreErrorCategory`
- `CoreErrorType`

### `AgentRunner`

高层 lifecycle facade。适合 host 不想每次手写 create run、mark running、调用 `RunKernel`、mark completed/failed 的场景。

```python
AgentRunner(
    *,
    run_persistence: RunPersistencePort,
    event_log: EventLogPort,
    llm_client: LLMClientPort,
    tool_executor: ToolExecutorLike | None = None,
    tool_observability: ToolObservabilityPort | None = None,
    tool_policy: CoreToolPolicy | None = None,
    run_observer: RunObserverLike | None = None,
    id_generator: IdGenerator | None = None,
)
```

核心方法：

```python
result = await runner.run(AgentRunnerRequest(...))
```

`AgentRunner` 仍然不拥有数据库事务。需要强事务边界的 host 应在 port 实现中处理，或继续直接使用 `RunKernel`。

`AgentRunnerResult` 包含 `run`、`completed`、`kernel_result`、`events` 和 `summary`。

### `RunKernel`

多轮 agent run 的核心执行器。

```python
RunKernel(
    *,
    llm_client: LLMClientPort,
    event_writer: CoreEventWriter,
    tool_executor: ToolExecutorLike | None = None,
    tool_observability: ToolObservabilityPort | None = None,
    tool_policy: CoreToolPolicy | None = None,
    id_generator: IdGenerator | None = None,
    clock: Callable[[], float] | None = None,
)
```

职责：

- 调用 `LLMClientPort.stream_turn()`；
- 调用 `TurnKernel` 执行每个 turn；
- 将 tool result 回灌成 transcript message；
- 汇总 usage、turn count、tool count；
- 执行 `RunLimits`；
- 返回 `RunKernelResult`。

核心方法：

```python
result = await kernel.run(request)
```

### `RunRequest`

```python
RunRequest(
    run_id: str,
    messages: tuple[Message, ...],
    tool_context: ToolExecutionContext,
    tools: tuple[ToolDefinition, ...] = (),
    model: str | None = None,
    system_prompt: str | None = None,
    limits: RunLimits = RunLimits(),
    metadata: dict[str, Any] = {},
    turn_offset: int = 0,
    cancellation_token: CancellationToken | None = None,
)
```

字段说明：

| 字段 | 含义 |
| --- | --- |
| `run_id` | host 分配或传入的 run id，必须和 `CoreEventWriter.run_id` 一致 |
| `messages` | 初始 transcript |
| `tool_context` | 工具执行上下文，承载 project/session/user_request 等 host 信息 |
| `tools` | 本次 run 暴露给模型的工具定义 |
| `model` | host 选择的模型名 |
| `system_prompt` | system prompt |
| `limits` | turn/tool/time/repeated-call 限制 |
| `metadata` | 透传到 turn started 事件的元数据 |
| `turn_offset` | continuation 场景下已提交 turn 数，确保 turn index 单调 |
| `cancellation_token` | 协作式取消令牌；取消后 stop reason 为 `cancelled`，不会继续发起新 turn 或执行后续工具 |

### `RunKernelResult`

```python
RunKernelResult(
    stop_reason: str,
    messages: tuple[Message, ...],
    turns_count: int,
    tool_calls_count: int,
    usage: Usage,
    turn_results: tuple[TurnKernelResult, ...],
    events: tuple[AgentEvent, ...],
    tool_results: tuple[ToolExecutionResult, ...],
)
```

常用字段：

- `stop_reason`：最终停止原因，例如 `end_turn`、`tool_use`、`max_turns`、`max_tool_calls`、`max_wall_clock`、`repeated_tool_call`、`pause_requested`；
- `messages`：追加 assistant/tool message 后的 transcript；
- `events`：本次 kernel run 写出的事件；
- `usage`：累计 token usage。

### `TurnKernel`

单 turn 执行器。大多数 host 优先使用 `RunKernel`；只有需要自定义 run loop 时才直接使用 `TurnKernel`。

```python
TurnKernel(
    *,
    llm_client: LLMClientPort,
    event_writer: CoreEventWriter,
    tool_executor: ToolExecutorLike | None = None,
    tool_observability: ToolObservabilityPort | None = None,
    tool_policy: CoreToolPolicy | None = None,
)
```

核心方法：

```python
turn_result = await kernel.run_turn(request)
```

### `TurnRequest`

```python
TurnRequest(
    run_id: str,
    turn_id: str,
    messages: Sequence[Message],
    tool_context: ToolExecutionContext,
    model: str | None = None,
    system_prompt: str | None = None,
    tools: Sequence[ToolDefinition] = (),
    turn_index: int = 0,
    metadata: Mapping[str, Any] = {},
    cancellation_token: CancellationToken | None = None,
)
```

### `TurnKernelResult`

```python
TurnKernelResult(
    stop_reason: str,
    raw_stop_reason: str,
    content: tuple[StandardContentBlock, ...],
    usage: Usage,
    tool_results: tuple[ToolExecutionResult, ...],
    invalid_tool_calls: tuple[InvalidToolCall, ...],
    events: tuple[AgentEvent, ...],
    pause_requested: bool = False,
    provider_state: Any | None = None,
)
```

### `LLMClientPort`

Host 需要实现的模型调用边界。

```python
class LLMClientPort(Protocol):
    def stream_turn(self, request: TurnRequest) -> AsyncIterable[StandardEvent]: ...
```

要求：

- 正常路径必须最终 yield 一个 `TurnDone`；
- 异常路径建议调用 provider parser session 的 `finalize_on_error()`，尽量保留 partial text/reasoning/tool args；
- 不要把 provider 私有 chunk 直接交给 core。

### `RunSummary`

运行级摘要，适合 host 写 metrics、trace、billing projection 或审计索引。

```python
RunSummary(
    run_id: str,
    status: str,
    stop_reason: str | None,
    usage: Usage = Usage(),
    turns_count: int = 0,
    tool_calls_count: int = 0,
    invalid_tool_calls_count: int = 0,
    event_count: int = 0,
    output_text: str = "",
    error_message: str | None = None,
    metadata: Mapping[str, Any] = {},
)
```

`AgentRunnerResult.summary` 会返回该对象；直接使用 `RunKernel` 的 host 可调用 `summarize_kernel_result()` 或 `summarize_failed_run()`。

### `RunObserverPort`

`AgentRunner` 的运行级观测 hook。同步和异步 observer 都支持：

```python
class RunObserverPort(Protocol):
    def record_run_summary(self, summary: RunSummary) -> None: ...

class AsyncRunObserverPort(Protocol):
    async def record_run_summary(self, summary: RunSummary) -> None: ...
```

observer 失败不会改变 run 的 completed/failed 状态；生产 host 应在 observer 内部处理自己的重试和告警。

### Error classification

Core 内置稳定错误分类：`CoreErrorCategory`、`CoreErrorType`、`classify_core_error()`、`core_error()`。

```python
CoreErrorCategory
CoreErrorType
classify_core_error(error_type)
core_error(error_type, message, category=None, details=None)
```

工具失败结果中的 `error.type` 保留具体原因，`error.category` 用于跨 provider / tool / policy 的统一聚合。当前分类包括 `tool_policy`、`tool_unavailable`、`tool_error`、`run_limit`、`cancelled`、`provider`、`invalid_tool_call`、`internal`。

### `ToolExecutorLike`

Core 支持同步或异步工具执行器：

```python
class ToolExecutorPort(Protocol):
    def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult: ...

class AsyncToolExecutorPort(Protocol):
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult: ...
```

### `CoreEventWriter`

`EventLogPort` 的轻量 facade。

```python
CoreEventWriter(
    event_log: EventLogPort,
    run_id: str,
    turn_id: str = "",
    idempotency_prefix: str | None = None,
)
```

常用方法：

```python
writer = CoreEventWriter(event_log, run_id="run-1")
turn_writer = writer.with_turn("turn-1")
event = turn_writer.append(
    "custom_event",
    {"value": 1},
    idempotency_key="turn-1:custom",
)
```

### `CoreEventType`

当前 core 事件类型：

- `turn_started`
- `text_delta`
- `reasoning_delta`
- `tool_call_started`
- `tool_call_delta`
- `tool_call_completed`
- `tool_call_invalid`
- `usage_update`
- `tool_started`
- `tool_completed`
- `tool_failed`
- `turn_paused`
- `turn_completed`

### `RunLimits`

```python
RunLimits(
    max_turns: int | None = None,
    max_tool_calls: int | None = None,
    timeout_ms: int | None = None,
    repeated_tool_call_threshold: int | None = None,
)
```

### `CoreToolPolicy`

```python
CoreToolPolicy(
    pause_tool_names: frozenset[str] = frozenset(),
    pause_stop_reason: str = "pause_requested",
    safety_policy: ToolSafetyPolicy = ToolSafetyPolicy(),
)
```

用于声明哪些工具执行成功后应停止当前 run，例如等待用户确认或外部异步任务。

### `ToolSafetyPolicy`

```python
ToolSafetyPolicy(
    allowed_tool_names: frozenset[str] | None = None,
    blocked_tool_names: frozenset[str] = frozenset(),
    require_confirmation_for_mutating_tools: bool = False,
    confirmed_tool_use_ids: frozenset[str] = frozenset(),
)
```

安全策略在工具 executor 之前执行。可能返回的 `error.type`：

- `tool_blocked`
- `tool_not_allowed`
- `tool_confirmation_required`

### Provider LLM clients

参考 `LLMClientPort` 实现：

```python
ProviderClientConfig(
    model: str,
    api_key: str,
    base_url: str,
    timeout: float = 60.0,
    max_tokens: int = 4096,
    extra_headers: Mapping[str, str] | None = None,
    profile: Any | None = None,
)

OpenAICompatLLMClient(
    config,
    adapter=None,
    transport=None,
    supports_function_calling=True,
    supports_stream_usage=True,
    reasoning_effort=None,
)
AnthropicNativeLLMClient(config, adapter=None, transport=None, thinking_budget_tokens=None)
```

这些 client 负责：

- 将 `TurnRequest.messages/tools` 转为 provider adapter 输入；
- 调用 `rd-llm-adapter` transport；
- 将 provider chunk 解析为 `StandardEvent`；
- 异常时优先调用 `finalize_on_error()` 保留 partial output。

### Business adapter APIs

`rd_agent_core.business` 用于隔离业务 agent：

```python
BusinessAgentProfile(kind, display_name, description="", metadata={})
BusinessTask(instruction, project_id, session_id=None, request_id=None, agent_kind="orchestrator", metadata={})
PromptSection(name, content, priority=0, metadata={})
VerificationPlan(required=False, tool_names=(), criteria=(), max_attempts=1, metadata={})
ArtifactDescriptor(artifact_id, name, kind, uri, mime_type=None, version=None, metadata={})
ArtifactManifest(artifacts=(), metadata={})
```

Ports：

```python
class ContextProviderPort(Protocol):
    def build_prompt_sections(self, *, task: BusinessTask, tool_context: ToolExecutionContext) -> Sequence[PromptSection]: ...

class BusinessToolProviderPort(Protocol):
    def list_tools(self, *, task: BusinessTask, tool_context: ToolExecutionContext) -> Sequence[ToolDefinition]: ...

class VerificationPolicyPort(Protocol):
    def build_verification_plan(self, *, task: BusinessTask, tool_context: ToolExecutionContext) -> VerificationPlan: ...

class ArtifactExtractorPort(Protocol):
    def extract_manifest(self, *, task: BusinessTask, content: Sequence[Any], tool_context: ToolExecutionContext) -> ArtifactManifest: ...

class BusinessAgentAdapter(
    ContextProviderPort,
    BusinessToolProviderPort,
    VerificationPolicyPort,
    ArtifactExtractorPort,
    Protocol,
):
    @property
    def profile(self) -> BusinessAgentProfile: ...
```

## rd_agent_core.testing

Testing harness 面向接入方公开使用。

### `AgentCoreHarness`

```python
AgentCoreHarness(
    *,
    llm_client: LLMClientPort,
    tool_executor: ToolExecutorLike | None = None,
    event_log: InMemoryEventLog | None = None,
    persistence: InMemoryRunPersistence | None = None,
    id_generator: DeterministicIdGenerator | None = None,
    timestamp_ms: int = 1_710_000_000_000,
)
```

核心方法：

```python
result = await harness.run(
    run_id: str | None = None,
    messages: Sequence[Message] = (),
    tools: Sequence[ToolDefinition] = (),
    tool_context: ToolExecutionContext | None = None,
    scope: RunScope | None = None,
    budget: RunBudget | None = None,
    limits: RunLimits | None = None,
    model: str | None = None,
    system_prompt: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    max_continuations: int = 0,
)
```

返回：

```python
HarnessRunResult(
    run: RunRecord,
    completed: RunRecord,
    kernel_result: RunKernelResult,
    events: tuple[AgentEvent, ...],
)
```

### Harness helpers

- `ScriptedLLMClient(turns)`：按 turn 输出固定 `StandardEvent` 序列；
- `FunctionToolExecutor(handlers)`：把 Python callable 包装成工具执行器；
- `InMemoryEventLog`：带 idempotency 的 per-run 事件日志；
- `InMemoryRunPersistence`：内存版 `RunPersistencePort`；
- `DeterministicIdGenerator`：生成稳定 run/turn/message/tool id。

## rd_agent_core.conformance

Conformance suite 面向外部 host，用来验证自己实现的 port 是否满足 SDK 最低语义。公开入口是 `assert_event_log_port_conformance()`、`assert_run_persistence_port_conformance()`、`assert_tool_executor_port_conformance()`。

- `assert_event_log_port_conformance`
- `assert_run_persistence_port_conformance`
- `assert_tool_executor_port_conformance`

```python
assert_event_log_port_conformance(event_log)
assert_run_persistence_port_conformance(persistence)
await assert_tool_executor_port_conformance(executor, request=...)
```

覆盖点：

- `EventLogPort` 的 idempotency、per-run seq、`from_seq` exclusive 语义；
- `RunPersistencePort` 的 root/running/completed/continuation parent/max_continuations 语义；
- `ToolExecutorPort` 的返回类型和 error shape。

## rd-agent-contracts

### Transcript

```python
Message(
    message_id: str,
    role: Literal["user", "assistant", "system", "tool"],
    content: str | list[dict[str, Any]],
    turn_id: str,
    tool_calls: list[ToolCall] = [],
    tool_results: list[ToolResult] = [],
)

ToolCall(tool_use_id: str, tool_name: str, input: dict[str, Any], status: ToolCallStatus)
ToolResult(tool_use_id: str, ok: bool, content: str, error: dict[str, Any] | None = None)
```

### Content blocks

`TurnDone.content` 的标准 block：

- `TextBlock(text, provider_data=None)`
- `ReasoningBlock(text="", signature=None, redacted=False, data=None, provider_data=None)`
- `ToolUseBlock(id, name, input={})`
- `InvalidToolCall(id, name, raw_args, parse_error, index, encoding=None)`

规则：

- `ToolUseBlock` 表示完整可执行工具调用；
- `InvalidToolCall` 永不执行，只记录和投影；
- 新代码应优先消费 `TurnDone.content`，不要把 `text_blocks`、`tool_calls` 当成独立 truth。

### Tool contracts

```python
ToolDefinition(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    mutates_workspace: bool = False,
    metadata: dict[str, Any] = {},
)

ToolExecutionContext(
    project_id: str,
    tenant_id: str | None = None,
    lease_id: str | None = None,
    correlation_id: str | None = None,
    session_id: str | None = None,
    user_request_id: str | None = None,
    agent_run_id: str | None = None,
    agent_kind: str = "orchestrator",
    subagent_task_id: str | None = None,
    metadata: dict[str, Any] = {},
)

ToolExecutionRequest(tool_name, tool_input, context, tool_use_id=None, turn=0)
ToolExecutionResult(ok, content, error=None, duration_ms=None, metadata={})
```

Ports：

```python
class ToolRegistryPort(Protocol):
    def list_tools(self, *, context: ToolExecutionContext) -> list[ToolDefinition]: ...

class ToolExecutorPort(Protocol):
    def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult: ...

class ToolObservabilityPort(Protocol):
    def record_tool_calls(self, records: list[ToolObservabilityRecord]) -> None: ...
```

### Event contracts

```python
AgentEvent(
    seq: int,
    timestamp_ms: int,
    run_id: str,
    turn_id: str,
    event_type: str,
    payload: dict[str, Any],
    schema_version: str = SCHEMA_VERSION,
    message_id: str | None = None,
    action_id: str | None = None,
)

EventDraft(event_type, payload, turn_id="", timestamp_ms=None, schema_version=SCHEMA_VERSION)
```

`EventLogPort`：

```python
class EventLogPort(Protocol):
    def append_event(
        self,
        run_id: str,
        draft: EventDraft,
        *,
        idempotency_key: str | None = None,
    ) -> AgentEvent: ...

    def stream_events(
        self,
        run_id: str,
        *,
        from_seq: int = 0,
        limit: int | None = None,
    ) -> Iterable[AgentEvent]: ...
```

实现要求：

- 同一 run 内 `seq` 必须单调递增；
- 同一个 `idempotency_key` 重放必须返回原事件，不写重复事件。
- core 事件 payload 详见 `docs/EVENT-PAYLOAD-SCHEMA.md`。

### Run persistence

```python
RunBudget(max_turns, max_tool_calls, max_wall_clock_s, total_timeout_s)
RunScope(user_request_id, project_id, session_id=None, parent_run_id=None, subagent_task_id=None, agent_kind="orchestrator", correlation_id=None)
RunCompletion(stop_reason, metadata=RunResultMetadata(), engine_state_json=None, completed_at_ms=None)
RunFailure(error_message, completed_at_ms=None)
RunRecord(...)
```

`RunPersistencePort`：

```python
class RunPersistencePort(Protocol):
    def create_root_run(self, *, scope: RunScope, budget: RunBudget, max_continuations: int = 0, run_id: str | None = None) -> RunRecord: ...
    def create_subagent_run(self, *, scope: RunScope, budget: RunBudget, max_continuations: int = 0, run_id: str | None = None) -> RunRecord: ...
    def create_continuation_run(self, *, previous_run_id: str, engine_state_json: str, run_id: str | None = None) -> RunRecord | None: ...
    def mark_running(self, run_id: str, *, started_at_ms: int | None = None) -> RunRecord | None: ...
    def mark_completed(self, run_id: str, *, completion: RunCompletion) -> RunRecord | None: ...
    def mark_failed(self, run_id: str, *, failure: RunFailure) -> RunRecord | None: ...
    def mark_resumed(self, run_id: str) -> RunRecord | None: ...
    def claim_latest_waiting_orchestrator_run(self, *, project_id: str) -> RunRecord | None: ...
    def load_run(self, run_id: str) -> RunRecord | None: ...
    def load_run_with_parent(self, run_id: str) -> tuple[RunRecord, RunRecord | None] | None: ...
```

### Continuation queue

```python
ContinuationJobSpec(user_request_id, project_id, previous_run_id, next_run_id, max_attempts=1, correlation_id=None, available_at_ms=None)
ContinuationJobRecord(...)
```

`ContinuationQueuePort` 定义：

- `enqueue_for_run`
- `claim_next`
- `mark_attempt_started`
- `heartbeat`
- `complete_success`
- `complete_failure`
- `release_for_retry`
- `reclaim_stale`
- `load_job`

### Usage

```python
Usage(
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
)
normalize_usage(raw)
```

注意：

- `cache_read_input_tokens` 和 `cache_creation_input_tokens` 是独立字段；
- legacy `cached_input_tokens` 兼容字段只用于输入兼容，不应作为额外 token 累加。

### Blob / provider lock

```python
BlobRef(content_bytes, content_sha256, mime_type, content_inline=None, content_ref=None, content_inline_truncated=False)
ProviderLock(provider_id, adapter_family, tool_protocol, reasoning_protocol, locked_at_run_id)
```

用途：

- `BlobRef` 表示大工具输出的 inline/ref/truncated 策略；
- `ProviderLock` 防止同一 transcript 在多轮中跨 provider family 导致 tool/reasoning 协议不兼容。

## rd-llm-adapter

### Standard events

Provider parser session 输出：

```python
TextDelta(text, block_index=0)
ReasoningDelta(text, block_index=0, provider_data=None)
ToolCallStart(index, call_id=None, name=None, encoding_hint=None)
ToolCallIdDelta(index, call_id)
ToolCallNameDelta(index, name_delta, call_id=None)
ToolCallArgsDelta(index, delta, call_id=None)
ToolCallEnd(call_id, name, index, encoding, raw_args, parsed_input, parse_error)
UsageUpdate(input_tokens=0, output_tokens=0, total_tokens=0, cache_read_input_tokens=0, cache_creation_input_tokens=0, cached_input_tokens=0, reasoning_tokens=0)
TurnDone(stop_reason, content, text_blocks, reasoning_blocks, tool_calls, invalid_tool_calls, sources=[], usage=None, provider_state=None, raw_stop_reason="")
```

### Parser session protocol

```python
class StreamParserSession(Protocol):
    def feed(self, raw_chunk: Any) -> Iterable[StandardEvent]: ...
    def finalize(self) -> Iterable[StandardEvent]: ...
    def finalize_on_error(self) -> Iterable[StandardEvent]: ...
```

规则：

- 每个 parser session 只处理一个 turn；
- 正常流结束调用 `finalize()`；
- provider stream 中途异常时调用 `finalize_on_error()`，用于保留 partial output；
- 如果没有 partial output，`finalize_on_error()` 可以不返回事件。

### Transport protocol

```python
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
```

### OpenAI-compatible adapter

```python
adapter = OpenAICompatAdapter()
request_body = adapter.build_request(
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    supports_function_calling: bool,
    supports_stream_usage: bool,
    reasoning_effort: Literal["low", "medium", "high"] | None = None,
)
session = adapter.create_parser_session(profile=None)
```

Transport：

```python
transport = OpenAICompatTransport()
async for chunk in transport.stream(request_body, api_key=..., base_url=..., timeout=60):
    ...
```

### Anthropic Native adapter

```python
adapter = AnthropicNativeAdapter()
request_body = adapter.build_request(
    model: str,
    system_prompt: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    max_tokens: int,
    profile: Any | None = None,
    thinking_budget_tokens: int | None = None,
)
session = adapter.create_parser_session(profile=None)
```

Transport：

```python
transport = AnthropicNativeTransport()
async for chunk in transport.stream(request_body, api_key=..., base_url="https://api.anthropic.com", timeout=60):
    ...
```

### Registry helpers

```python
supported_adapter_kinds() -> tuple[str, ...]
supported_transport_kinds() -> tuple[str, ...]
resolve_adapter(adapter_kind: str) -> Any
resolve_transport(adapter_kind: str) -> Any
resolve_adapter_for_profile(profile: Any) -> Any
resolve_transport_for_profile(profile: Any) -> Any
```

当前 adapter kind：

- `openai_compat`
- `anthropic_native`

## 最小生产接入清单

接入方至少需要实现：

1. `EventLogPort`
2. `LLMClientPort`
3. `ToolExecutorPort`
4. `RunPersistencePort`

建议随后实现：

5. `ToolRegistryPort`
6. `ToolObservabilityPort`
7. `ContinuationQueuePort`
8. UI projection / billing / audit / replay

发布前必须覆盖的 smoke：

- text-only run；
- single-tool run；
- multi-turn tool loop；
- invalid tool call 不执行；
- `max_tool_calls` 生效；
- event log idempotency；
- run persistence continuation parent linkage。

## Reference host

`examples/reference_host` 提供一套可运行的 SQLite 示例，帮助接入方理解 host ports 的生产形态。

包含：

- `SQLiteEventLog`：实现 `EventLogPort`；
- `SQLiteRunPersistence`：实现 `RunPersistencePort`；
- `SQLiteContinuationQueue`：实现 `ContinuationQueuePort`；
- `ReferenceContinuationWorker`：展示 continuation worker 生命周期骨架；
- `connect_sqlite_reference_host()`：创建共享 SQLite connection；
- `python -m examples.reference_host.demo`：运行一条 deterministic single-tool demo。

注意：

- 这是 example-only，不是 SDK 稳定 API；
- SQLite schema 不属于兼容性承诺；
- 生产 host 应保留 port 语义，替换为自己的数据库、事务、队列、安全和观测实现。
