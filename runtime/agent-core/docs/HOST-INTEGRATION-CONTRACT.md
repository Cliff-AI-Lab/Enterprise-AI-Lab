# Host Integration Contract

`rd-agent-core` 是可复用运行底座，不是一个带产品假设的应用框架。Host 可以是 SaaS、CLI、本地桌面、任务队列 worker 或未来 PaaS 服务；它们通过 `rd-agent-contracts` port 注入能力，并对安全、持久化和投影负责。

## Core 负责

- 消费 `rd-llm-adapter` 的标准流事件，形成稳定的 turn/run 语义；
- 将 `TextDelta`、`ReasoningDelta`、tool call lifecycle、usage、turn completed 写入 `EventLogPort`；
- 执行完整且可解析的 `ToolUseBlock`，拒绝 invalid tool call；
- 将 tool result 回灌为 transcript message，驱动多轮 LLM/tool loop；
- 执行运行边界：`max_turns`、`max_tool_calls`、timeout、重复工具调用保护、pause tool 停止；
- 输出 `RunKernelResult`，让 host 可以落库、排队、投影或继续执行。

## Host 必须提供

- `LLMClientPort`：把模型网关或 provider adapter 封装成 `stream_turn()`，并保证每个正常 turn 以 `TurnDone` 收敛；
- `EventLogPort`：按 run 分配单调递增 `seq`，并支持 idempotency key 重放不重复写入；
- `ToolExecutorPort`：执行业务工具，返回结构化 `ToolExecutionResult`；
- `RunPersistencePort`：持久化 run lifecycle，至少覆盖 pending、running、completed、failed、continuable/resuming；
- 可选 `ToolObservabilityPort`：记录工具执行审计、耗时、错误和脱敏后的输入输出；
- 可选 `ContinuationQueuePort`：把超时、等待用户或预算耗尽后的 continuation 交给 host 队列。

## Host 保留的职责

- 身份、租户、项目权限、workspace lease、文件系统和网络访问控制；
- tool registry 与 profile 过滤，确保模型只能看到本次 run 允许的工具；
- tool input 的业务级 schema 校验、路径归一化、危险操作二次确认；
- provider base URL/API key/model profile 管理，以及超时、重试、限流；
- event 投影到 SSE/WebSocket/UI、billing/metering、artifact 存储；
- continuation 的事务边界：run 状态、队列任务、会话状态必须由 host 原子化协调；
- 日志、trace、录制、PII 脱敏和合规保留策略。

## 禁止穿透

- core 不 import `app.*`、ORM、Web framework、Redis、S3、workspace 或 UI 模型；
- core 不硬编码业务工具名、产品 route、数据库表、租户权限或 billing 规则；
- provider 私有 chunk 不进入 core；它们必须先在 adapter 层归一化；
- invalid/partial tool call 不交给 tool executor。半截 JSON、非 object JSON 和解析失败的工具调用只能进入 `invalid_tool_calls` 与事件日志；
- host 不应绕过 `EventLogPort` 直接拼核心事件，否则 continuation 和 replay 无法保持一致。

## 最小接入顺序

1. 实现 `EventLogPort`，并用 idempotency key 测试重复 append；
2. 实现 `LLMClientPort`，要求成功路径必定 emit `TurnDone`，异常路径尽量通过 adapter `finalize_on_error()` 保留 partial output；
3. 实现 `ToolExecutorPort`，先接只读工具，再接写工具和 pause tool；
4. 用 `RunKernel` 跑 text-only、single-tool、multi-turn、invalid-tool、max-tool-calls 五条 smoke；
5. 接入 `RunPersistencePort`，把 `RunKernelResult` 的 stop reason、usage、turn/tool count 和 engine state 落库；
6. 再接 continuation queue、UI projection、billing 和 artifact pipeline。

## Release Gate

发布前至少运行：

```bash
uv run pytest
uv run ruff check .
uv build --wheel packages/rd-agent-contracts
uv build --wheel packages/rd-llm-adapter
uv build --wheel packages/rd-agent-core
uv run python tools/scripts/verify_wheel_install.py rd-agent-core --dist-dir dist
```

Host 集成侧还必须有一条本地烟测，覆盖 `EventLogPort + RunPersistencePort + RunKernel + ToolExecutorPort` 的完整闭环。仓库内的 `packages/rd-agent-core/tests/test_local_host_smoke.py` 是最小参考实现。

## Harness

`rd_agent_core.testing` 提供可复用 harness，避免每个 host 重写私有假件：

- `InMemoryEventLog`：带 per-run sequence 与 idempotency 的事件日志；
- `InMemoryRunPersistence`：覆盖 `RunPersistencePort` 生命周期方法；
- `ScriptedLLMClient`：用标准事件脚本模拟多轮 LLM；
- `FunctionToolExecutor`：用 Python callable 注册工具 handler；
- `AgentCoreHarness`：一键跑 `RunKernel`，并返回 run record、kernel result 与完整事件流。

最小用法：

```python
from rd_agent_core.testing import AgentCoreHarness, FunctionToolExecutor, ScriptedLLMClient

harness = AgentCoreHarness(
    llm_client=ScriptedLLMClient([first_turn_events, second_turn_events]),
    tool_executor=FunctionToolExecutor({"lookup": lookup_handler}),
)
result = await harness.run(run_id="run-local", tools=[lookup_definition])
assert result.completed.stop_reason == "end_turn"
```
