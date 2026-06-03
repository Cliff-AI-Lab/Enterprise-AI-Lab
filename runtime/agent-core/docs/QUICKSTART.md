# Quickstart

这份文档面向要把 `rd-agent-core` 接入自己产品的 host。`rd-agent-core` 只提供运行底座，不接管用户、项目权限、工具注册、文件系统、计费、UI 投影和队列事务。

## 安装

开发期推荐直接从 workspace 安装：

```bash
git clone https://github.com/shinelee211-arch/ruidong-agent-core.git
cd ruidong-agent-core
uv sync --all-extras
```

作为外部项目依赖时，使用同一批 release wheel：

```bash
uv add rd-agent-contracts==1.14.1
uv add rd-llm-adapter==1.1.2
uv add rd-agent-core==0.1.3
```

如果包还没有发布到私有索引，可以从 GitHub Releases 下载对应 wheel 后本地安装。

## 最小本地烟测

`rd_agent_core.testing` 提供 host 接入 harness。它不是生产实现，而是让接入方在没有数据库、队列和真实模型的情况下先验证事件、持久化、工具执行和 run 结果闭环。

```python
from rd_agent_contracts import TextBlock, ToolDefinition, ToolExecutionRequest
from rd_agent_core.testing import AgentCoreHarness, FunctionToolExecutor, ScriptedLLMClient
from rd_llm_adapter import TurnDone


def final_turn(_request):
    text = TextBlock("done")
    return [
        TurnDone(
            stop_reason="end_turn",
            content=[text],
            text_blocks=[text],
            reasoning_blocks=[],
            tool_calls=[],
            invalid_tool_calls=[],
            raw_stop_reason="stop",
        )
    ]


def lookup(request: ToolExecutionRequest) -> str:
    return f"lookup:{request.tool_input['id']}"


lookup_tool = ToolDefinition(
    name="lookup",
    description="Lookup by id",
    input_schema={
        "type": "object",
        "properties": {"id": {"type": "string"}},
        "required": ["id"],
    },
)

harness = AgentCoreHarness(
    llm_client=ScriptedLLMClient([final_turn]),
    tool_executor=FunctionToolExecutor({"lookup": lookup}),
)

result = await harness.run(tools=[lookup_tool])
assert result.completed.stop_reason == "end_turn"
assert result.events
```

更完整的 single-tool、多轮、idempotency、continuation parent linkage 参考 `packages/rd-agent-core/tests/test_local_host_smoke.py`。

如果需要看接近生产 host 的持久化形态，参考 `examples/reference_host`。它提供 SQLite 版 `EventLogPort` 和 `RunPersistencePort`，并包含一条可运行的 `RunKernel` 闭环 demo。

## Host 接入顺序

1. 实现 `EventLogPort`，确保同一 run 内 `seq` 单调递增，并用 idempotency key 测重复 append。
2. 实现 `LLMClientPort`，正常路径必须以 `TurnDone` 收敛，异常路径优先调用 adapter 的 `finalize_on_error()` 保留 partial output。
3. 实现 `ToolExecutorPort`，先接只读工具，再接写工具和 pause tool。
4. 用 `RunKernel` 跑 text-only、single-tool、multi-turn、invalid-tool、max-tool-calls 五条 smoke。
5. 接 `RunPersistencePort`，把 stop reason、usage、turn/tool count 和 engine state 落库。
6. 跑 `rd_agent_core.conformance`，把 `EventLogPort`、`RunPersistencePort`、`ToolExecutorPort` 的最低语义纳入宿主 CI。
7. 再接 continuation queue、UI projection、billing、artifact pipeline 和生产级 observability。

生产接入可以从 `AgentRunner` 开始。它会按顺序调用 `RunPersistencePort.create_root_run()`、`mark_running()`、`RunKernel.run()`、`mark_completed()` / `mark_failed()`，并返回 `RunSummary` 供 metrics、trace、billing projection 使用。需要更强事务边界时，仍可直接使用 `RunKernel`。

## 发布前验证

```bash
uv run ruff check .
uv run pytest
uv build --wheel packages/rd-agent-contracts
uv build --wheel packages/rd-llm-adapter
uv build --wheel packages/rd-agent-core
```

推荐 release tag：

- `rd-agent-contracts-v1.14.1`
- `rd-llm-adapter-v1.1.2`
- `rd-agent-core-v0.1.3`
