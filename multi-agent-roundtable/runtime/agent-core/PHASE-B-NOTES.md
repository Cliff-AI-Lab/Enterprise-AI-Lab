# Phase B 启动备忘录

**状态**：历史启动备忘录。当前代码基线以 `main` + README 为准；本文件保留 Phase B 分层和风险点背景。

**适用仓库**：`ruidong-agent-core` + `codesphere-saas`

---

## 1. 当前基线

Phase A 已完成，历史 tag：`phase-a-complete`。当前 `main` 已包含后续 Phase B 资产；下面的 `feature/phase-a` 启动命令仅作为历史记录保留：

```bash
cd ~/ruidong/ruidong-agent-core
git checkout feature/phase-a
git pull --ff-only origin feature/phase-a
git log --oneline -5
git tag --contains 5ace0e3
```

不要再按旧备忘录从 `feature/phase-a` 重新起步；继续工作应以当前 `main` 为基线。

Phase A 资产：

| 层 | 包 | 资产 |
|---|---|---|
| 数据契约 | `rd-agent-contracts` | ID / StopReason / ToolCallStatus / Message / Usage / BlobRef / BudgetEnvelope / ProviderLock / AgentEvent / 横切 ports / Clock |
| LLM 网关 v1 | `rd-llm-gateway` | StreamChunk / StreamNormalizer / ChatRequest / LLMProvider / OpenAICompatProvider |
| Replay 工具链 | `rd-replay-evals` | GoldenTrace / RecordingEventSink / MockLLMProvider / MockToolExecutor / 5 条一致性检查 |
| 运维工具 | `rd-tools` | dump_run CLI + finalize_traces.py |
| codesphere 接入 | `app/services/rd_recorder.py` | ENV-gated fan-out hook：`RD_RECORD_TRACES=1` |
| 真实数据 | `traces/golden/` | 3 个真实 chat session trace，637 行 jsonl |

`rd-llm-gateway v1` 是 Phase A 产物，但不是 Phase B 的 engine 边界。它会被保留为历史产物，Phase B 不让 `rd-agent-core` 依赖 v1 的 6-chunk 形态。

---

## 2. Phase B 第一原则

Phase B 的目标是把 codesphere-saas 的 agent runtime 抽成可复用 PaaS 组件。当前正确分层：

1. `rd-llm-adapter`：低层 provider adapter，承载 `StandardEvent` / `TurnDone` / capabilities / raw chunk replay。
2. `rd-agent-contracts`：跨包共享契约，Phase B 需要补 typed transcript block、ProviderState、EventDraft 等共享类型。
3. `rd-agent-core`：P5 engine，只依赖 contracts、ports 和注入的 LLM port，不直接依赖 gateway v1。
4. `rd-llm-gateway` v2：后置 channel router/provider lock 实施包，内部依赖 `rd-llm-adapter`，由宿主通过 DI 注入给 core。
5. `rd-saas-adapter`：codesphere-saas 的 ports 适配层，B 阶段 vendored 在 `codesphere-saas/packages/rd-saas-adapter/`。

不要把 `model_adapter` 直接搬成 `rd-llm-gateway v2`。先建 `rd-llm-adapter`，gateway 后续只做路由与 provider lock。

---

## 3. 已知真实 model_adapter 状态

codesphere-saas 当前的 `app/services/agent_runner/model_adapter/` 已经不是旧备忘录里的单 OpenAI adapter 状态。启动 Phase B 前必须按当前源码为准：

- `OpenAICompatAdapter` / `OpenAICompatTransport`
- `AnthropicNativeAdapter` / `AnthropicNativeTransport`
- `StreamParserSession` 协议
- `TextDelta` / `ReasoningDelta` / `ToolCallStart` / `ToolCallIdDelta` / `ToolCallNameDelta` / `ToolCallArgsDelta` / `ToolCallEnd` / `UsageUpdate` / `TurnDone`
- `TextBlock` / `ReasoningBlock` / `ToolUseBlock` / `InvalidToolCall`
- `ModelCapabilities` / `ProtocolLimits` / `ThinkingExtractionConfig`
- `StreamRecorder` / `RecordedTurn` / raw chunk replay
- Anthropic signed thinking、redacted thinking fixtures
- recorded request redaction gate

B-1 不是“实现 AnthropicNativeAdapter”，而是“把已实现 adapter + fixtures + tests 原样移植到 `rd-llm-adapter`，并切 codesphere-saas import”。

---

## 4. B-0：reasoning_effort 生产 hotfix

B-0 是 Phase B 启动门槛，不属于抽象迁移本身。目标是修复前端传 `reasoning_effort` 但后端丢弃的问题。

必须补齐的链路：

```text
ActProxyRequest.reasoning_effort
  -> user message metadata_json["reasoning_effort"]
  -> UserRequest.result_metadata["reasoning_effort"] 或等价 JSON metadata
  -> AgentRunExecutionContext.reasoning_effort
  -> ResolvedModelProfile per-request overlay
  -> adapter.build_request(...)
```

Anthropic extended thinking 约束：

- `budget_tokens` 必须小于最终传给 provider 的 `max_tokens`。
- `prompt_tokens + max_tokens` 不能超过模型 context window。
- 如果模型/channel 的 `max_output_tokens` 或 context window 不支持某一档，该档必须从 `/models` 返回的 `supported_tiers` 里隐藏，不能在后端静默降级。

建议 B-0 映射形态：

| ReasoningEffort | Anthropic budget_tokens | Anthropic min max_tokens | OpenAI Responses |
|---|---:|---:|---|
| THINK | 4000 | 8192 | low |
| THINK_HARD | 8000 | 12000 | medium |
| THINK_HARDER | 20000 | 26000 | high |
| ULTRATHINK | 48000 | 64000 | 不显示 |

激活路径：

- B-0 不要求 DB schema 改动。
- 可以用现有 `model_channels.models` JSON override 配置 Claude 系列：`sdk_type=anthropic_native`、`base_url`、`supports_thinking=true`。
- saas-test 必须打开 `MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME=1`，并用 allowlist 灰度 `anthropic_native`。
- B-0 不做“按 reasoning_effort 自动把任意模型切 native”。只对 capabilities 声明支持 thinking control 的模型显示选择器并透传。

验收：

- 单元测试覆盖 4 档映射、`max_tokens > budget_tokens`、unsupported tier 隐藏。
- API 集成测试证明 `/models` 返回 `reasoning_effort.supported/supported_tiers`。
- 后台 AgentRun 测试证明 `reasoning_effort` 从 HTTP request 持久化到 executor context。
- saas-test 抓真实 LLM request body，确认 `thinking.budget_tokens` 或 `reasoning_effort` 真传出。
- saas-test 至少 2 天无生产报错，再考虑 prod。

---

## 5. B-1：rd-llm-adapter 移植

B-1 的包目标：

```text
ruidong-agent-core/packages/rd-llm-adapter/
```

迁移内容：

1. 迁移 `codesphere-saas/app/services/agent_runner/model_adapter/` 源码。
2. 迁移 `codesphere-saas/docs/design/MODEL-ADAPTER.md` 到 `ruidong-agent-core/docs/MODEL-ADAPTER.md`。
3. 迁移 adapter 相关测试和 fixtures，尤其是 Anthropic native fixtures 与 recorded fixtures。
4. 切换 codesphere-saas import 到 `rd_llm_adapter`。
5. 删除 codesphere-saas 原 `model_adapter/` 目录，结束双写窗口。

B-1 必须有两条 replay 线：

| replay 线 | 目的 | 输入 | 验收 |
|---|---|---|---|
| Adapter raw fixture replay | 证明 provider 边界无损 | `RecordedTurn.raw_chunks` / Anthropic fixture stream | StandardEvent、TurnDone、legacy event diff 全一致 |
| Engine AgentEvent golden trace | 证明业务行为不变 | `traces/golden/*.jsonl` + post-D baseline | event 序列、tool call set、stop_reason、usage、语义断言一致 |

Adapter raw replay 必须覆盖：

- Anthropic signed thinking signature byte-equal。
- redacted thinking data byte-equal。
- invalid tool call 顺序保留。
- usage-only / empty response / stream interruption。
- request body redaction gate。

Contracts 前置：

- `ProviderLock.reasoning_protocol` 字段已经存在；Phase B 只需要补兼容判断和读取/写入策略。
- 在 engine 抽出前，`rd-agent-contracts` 需要补 typed transcript contract：`TextBlock`、`ReasoningBlock`、`ToolUseBlock`、`InvalidToolCall`、`ProviderState`、`StandardContentBlock`。
- 这些共享 transcript 类型不应只留在 `rd-llm-adapter`，否则 `rd-agent-core` 和 persistence ports 会形成第二套 transcript 表达。

---

## 6. B-2：persistence + event ports

B-2 只抽第一批可落地 ports：

- `RunPersistencePort`
- `EventLogPort`
- `ContinuationQueuePort`

当前 contracts 进展：`rd-agent-contracts` 开发版 `1.4.0` 已补 `RunPersistencePort`、`EventDraft` / `EventLogPort`、`ContinuationQueuePort` 和 run lifecycle policy helpers。SaaS 侧适配器已在 `codesphere-saas` 本地接入；发布部署前需要推送 `rd-agent-contracts-v1.4.0` release 并把 SaaS 依赖切回可安装来源。

EventLog seq 决策：

- EventLogPort 负责分配 `AgentEvent.seq`。
- 调用方提交 `EventDraft`，不提交完整 `AgentEvent`。
- `append_event(run_id, draft, idempotency_key=None) -> AgentEvent` 返回已分配 seq 的事件。
- contract tests 必须覆盖并发 append 单调递增、idempotency_key 重放不重复写、`stream_events(from_seq)` 从指定 seq 后继续。

ContinuationQueue 决策：

- `ContinuationQueuePort` 只暴露 `ContinuationJobSpec` / `ContinuationJobRecord` / 队列状态，不暴露 ORM model。
- `claim_next` 的具体锁策略由 host adapter 实现；SaaS adapter 在 PostgreSQL 使用 `FOR UPDATE SKIP LOCKED`，SQLite 测试使用有序查询。
- retry delay、max attempts 默认值仍由 host 配置决定；contracts 只定义显式字段和状态迁移。

`rd-saas-adapter` 放在 `codesphere-saas/packages/rd-saas-adapter/`。B 阶段允许有限 app import，但必须写清边界：

- 允许：`app.models.*`、`app.db.*`、SQLAlchemy session 相关类型。
- 禁止：`app.services.*` 业务服务反向 import。
- CI 用 allowlist 检查，而不是简单禁止所有 `from app.`。

Phase C 再把 ORM model 抽到独立 `codesphere-models` 包。

---

## 7. B-3：engine 抽出

`rd-agent-core` 只依赖：

- `rd-agent-contracts`
- `rd-llm-adapter` 的标准事件/消息类型，或已提升到 contracts 的共享 transcript 类型
- ports protocol

`rd-agent-core` 不直接依赖 `rd-llm-gateway v1`。如需 channel router：

```text
rd-llm-gateway v2 implements LLMClientPort
codesphere-saas / rd-server-fastapi injects gateway into rd-agent-core
```

ProviderLock 规则：

- 新 run 第一次 LLM 调用成功收到 chunk 后写 lock。
- lock 内容包含 `provider_id`、`adapter_family`、`tool_protocol`、`reasoning_protocol`、`locked_at_run_id`。
- `is_compatible_with` 必须比较 `reasoning_protocol`。
- B-3 之前的老 run 可容忍 lock=None，但新 run 必须强制 lock。

---

## 8. 启动检查清单

```bash
cd ~/ruidong/ruidong-agent-core
git checkout feature/phase-a
git pull --ff-only origin feature/phase-a
uv run pytest
uv run ruff check .
```

```bash
cd ~/ruidong/codesphere-saas
git checkout newsaas
git status --short
git log --oneline -5
```

如果需要补 AgentEvent traces：

```bash
ssh root@13.221.2.57 "ls -la /tmp/rd_traces/"
mkdir -p /tmp/rd_traces_dump_$(date +%F)
scp 'root@13.221.2.57:/tmp/rd_traces/*.jsonl' /tmp/rd_traces_dump_$(date +%F)/

cd ~/ruidong/ruidong-agent-core
uv run python tools/scripts/finalize_traces.py \
  --input-dir /tmp/rd_traces_dump_$(date +%F) \
  --output-dir traces/golden
uv run pytest packages/rd-replay-evals/tests/test_golden_traces_self_consistent.py -v
```

如果 ENV 还开着，补完 trace 后及时关闭，防止 saas-test 占盘：

```bash
ssh root@13.221.2.57 "
sed -i '/^RD_RECORD_TRACES/d; /^RD_RECORD_DIR/d; /^# Phase A B+/d' /root/codesphere/.env.saas-test
"
cd ~/ruidong/codesphere-saas
bash sync_saas_test.sh --restart
```

---

## 9. 关键路径

| 路径 | 用途 |
|---|---|
| `~/ruidong/ruidong-agent-core/PHASE-B-NOTES.md` | 本文档 |
| `~/ruidong/codesphere-saas/docs/superpowers/specs/2026-05-02-phase-b-design.md` | Phase B 正式 spec |
| `~/ruidong/codesphere-saas/docs/design/MODEL-ADAPTER.md` | model_adapter 设计 |
| `~/ruidong/codesphere-saas/app/services/agent_runner/model_adapter/` | B-1 移植源 |
| `~/ruidong/codesphere-saas/app/services/agent_runner/engine.py` | B-3 抽出目标 |
| `~/ruidong/codesphere-saas/app/services/rd_recorder.py` | Phase A AgentEvent trace hook |
| `~/ruidong/ruidong-agent-core/traces/golden/*.jsonl` | Phase A golden traces |
