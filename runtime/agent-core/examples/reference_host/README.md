# Reference Host Example

这个目录展示一个最小但完整的 host 接入形态。它不是 SDK 稳定 API，也不是生产数据库实现；它的职责是给接入方一份可运行、可测试、可照着改的参考。

## 包含内容

- `SQLiteEventLog`：SQLite 版 `EventLogPort`，支持 per-run sequence 与 idempotency key；
- `SQLiteRunPersistence`：SQLite 版 `RunPersistencePort`，支持 root run、subagent run、continuation run、parent linkage 和 lifecycle update；
- `SQLiteContinuationQueue`：SQLite 版 `ContinuationQueuePort`，展示 claim、attempt、retry、dead-letter 和 stale reclaim 语义；
- `continuation_worker.py`：基于公开 queue contract 的轻量 worker 示例；
- `connect_sqlite_reference_host()`：创建共享 SQLite connection 的 reference host；
- `demo.py`：用 `RunKernel + ScriptedLLMClient + FunctionToolExecutor` 跑一条 single-tool 多轮闭环。

## 运行

```bash
uv run python -m examples.reference_host.demo
```

预期输出类似：

```json
{
  "run_id": "run-reference",
  "status": "completed",
  "stop_reason": "end_turn",
  "turns_count": 2,
  "tool_calls_count": 1,
  "event_count": 9
}
```

## 接入方应替换的部分

- 把 SQLite schema 换成自己的 SQL/ORM migration；
- 给 `append_event()` 和 run lifecycle update 增加生产级事务边界；
- 将 `ScriptedLLMClient` 换成真实 `LLMClientPort`；
- 将 `FunctionToolExecutor` 换成自己的 tool runtime；
- 在 `ToolExecutionContext` 中接入租户、权限、workspace lease 和 correlation id；
- 把事件投影到 UI、SSE/WebSocket、billing、audit 和 replay。

## 不应直接照搬的部分

- 这个示例没有做租户隔离；
- 没有实现 provider 重试、限流或 API key 管理；
- continuation worker 只展示生命周期骨架，没有生产级并发锁和队列调度；
- 没有处理大工具输出的 blob 生命周期；
- 没有完整的安全策略、PII 脱敏和合规保留。

生产 host 应以这里的 port 语义为准，而不是以 SQLite 表结构为准。
