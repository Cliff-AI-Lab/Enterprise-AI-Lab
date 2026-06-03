# API Stability Policy

本文档定义 `ruidong-agent-core` 作为 SDK 对外承诺的稳定性边界。目标是让接入方知道哪些接口可以依赖，哪些仍处于 0.x 迭代阶段。

## 当前状态

当前版本：

- `rd-agent-contracts==1.14.1`
- `rd-llm-adapter==1.1.2`
- `rd-agent-core==0.1.3`

`rd-agent-contracts` 和 `rd-llm-adapter` 已经按 SemVer 风格维护。`rd-agent-core` 仍是 `0.x`，表示核心方向稳定，但运行 API 会根据真实 host 接入反馈继续收紧。

## 稳定性分级

### Stable Contract

这些接口是接入方当前可以依赖的主路径。破坏性变化会尽量避免；如果必须发生，会提供 migration note。

- `rd_agent_contracts` 中已在 `docs/API-REFERENCE.md` 列出的 dataclass；
- `EventLogPort` 的 append/stream 语义；
- `RunPersistencePort` 的 run lifecycle 语义；
- `ToolDefinition`、`ToolExecutionContext`、`ToolExecutionRequest`、`ToolExecutionResult`；
- `TextBlock`、`ReasoningBlock`、`ToolUseBlock`、`InvalidToolCall`；
- `rd_llm_adapter.events` 的标准事件集合；
- `StreamParserSession.feed/finalize/finalize_on_error` 语义；
- `rd_agent_core.testing` 的 harness 主路径。
- `rd_agent_core.conformance` 的 port conformance 检查入口。

### Provisional Runtime API

这些接口是 SDK 的核心，但在 `rd-agent-core < 1.0` 阶段仍允许小幅调整。

- `RunKernel`
- `RunRequest`
- `RunKernelResult`
- `AgentRunner`
- `AgentRunnerRequest`
- `AgentRunnerResult`
- `RunSummary`
- `RunObserverPort`
- `OpenAICompatLLMClient`
- `AnthropicNativeLLMClient`
- `ProviderClientConfig`
- `TurnKernel`
- `TurnRequest`
- `TurnKernelResult`
- `CoreToolPolicy`
- `ToolSafetyPolicy`
- `RunLimits`
- `BusinessAgentAdapter` 相关协议

调整原则：

- 不为内部重构改 API；
- 只为接入清晰度、真实 host 缺口或错误语义修正改 API；
- 如果改动影响接入方，必须更新 `docs/API-REFERENCE.md` 和 release note。

### Example Only

这些内容是示例或测试支撑，不承诺作为 SDK API：

- `examples/reference_host` 的 SQLite schema；
- `examples/reference_host` 的 helper 方法；
- `packages/*/tests` 内的测试 fixture；
- `packages/rd-llm-adapter/tests_external`；
- `rd-llm-gateway` Phase A 包。

接入方可以照着实现，但不应直接把 example 的表结构或 helper 当成长期兼容接口。

## 版本策略

### 0.x 阶段

`rd-agent-core` 在 `0.x` 阶段采用以下约定：

- patch 版本：bugfix、文档、示例、测试、非破坏性新增；
- minor 版本：可能包含破坏性调整，但必须有 migration note；
- 不在 patch 版本中故意破坏 `docs/API-REFERENCE.md` 中的主路径接口。

### 1.x 阶段

进入 `1.0` 后按 SemVer：

- patch：向后兼容 bugfix；
- minor：向后兼容新增能力；
- major：破坏性变更。

## 弃用策略

进入 `1.0` 前：

- 如果接口命名明显错误、语义不完整，可以直接在 minor 版本调整；
- patch 版本只做兼容修复；
- 重要变更必须在 release note 中说明。

进入 `1.0` 后：

- 能保留兼容层的旧接口至少保留一个 minor 版本；
- 文档会标注 deprecated；
- 新接口必须在 `docs/API-REFERENCE.md` 中给出替代路径。

## 文档与发布同步

每次发布 SDK 包时必须检查：

- `README.md` 中版本号；
- `docs/API-REFERENCE.md` 包版本表；
- `docs/SDK-OVERVIEW.md` 当前发布形态；
- `docs/QUICKSTART.md` 安装命令；
- `docs/releases/` 对应 release note。

发布 tag 指向的仓库快照就是该版本的 versioned docs。main 分支文档代表下一版或当前开发态。

## 接入方兼容性建议

接入方应依赖：

- documented dataclass 字段；
- Protocol 方法签名；
- `RunKernel` / `TurnKernel` 的 documented request/result；
- `AgentEvent` 的 `event_type` 和 payload 中已文档化字段。

接入方不应依赖：

- 私有函数或下划线方法；
- provider 原始 chunk；
- example SQLite 表结构；
- 测试 fixture；
- 未出现在 `docs/API-REFERENCE.md` 的内部 helper。
