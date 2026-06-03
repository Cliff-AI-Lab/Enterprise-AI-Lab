# rd-agent-core v0.1.3

## 变更

- 新增协作式 cancellation token，`RunRequest`、`TurnRequest`、`AgentRunnerRequest` 均可接收，取消后的 stop reason 为 `cancelled`。
- 新增 `RunSummary`、`RunObserverPort` / `AsyncRunObserverPort`，`AgentRunnerResult` 会返回结构化摘要。
- 新增 `rd_agent_core.conformance`，提供 `EventLogPort`、`RunPersistencePort`、`ToolExecutorPort` 的可执行接入检查。
- 新增稳定错误分类 helper：`CoreErrorCategory`、`CoreErrorType`、`classify_core_error()`、`core_error()`。
- Reference host 新增 SQLite continuation queue 和 lightweight continuation worker 示例。
- 增加公开 API 快照、文档一致性、typed marker、conformance 和 continuation queue 回归测试。

## 兼容性

- 这是 `rd-agent-core` 的 patch 版本。新增字段均有默认值；直接构造 `AgentRunnerResult` 的测试代码需要传入新增 `summary` 字段。
- `ToolExecutionResult.error` 中 core 生成的错误现在会包含 `category` 字段；既有 `type` 和 `message` 保留。

## 依赖

- `rd-agent-contracts>=1.14.1,<2.0.0`
- `rd-llm-adapter>=1.1.2,<2.0.0`
