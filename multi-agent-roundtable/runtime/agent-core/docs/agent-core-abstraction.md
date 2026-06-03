# Agent Core 抽象边界

## 当前切片

`rd-agent-core` 现在只承担可复用运行底座：

- turn kernel：消费 `rd-llm-adapter` 的标准事件，写入 `AgentEvent`，执行完整 tool call；
- run kernel：在 core 内完成多轮 LLM/tool 循环、tool result 回灌、usage 汇总、pause 停止、timeout 与重复工具调用保护；
- 业务 Agent adapter 协议：业务侧提供 prompt sections、tools、verification plan、artifact manifest；
- event writer：只依赖 `EventLogPort`，不持有数据库、SSE、前端或租户假设；
- policy helpers：run limit 与重复 tool call 检测保持纯函数。

## SaaS 接入方式

CodeSphere SaaS 侧已有 `SaasEventLog` / `SaasRunPersistence` / `SaasContinuationQueue` 等 `rd-agent-contracts` port 实现。安全接入方式是由 SaaS 注入这些 adapter：

```python
from rd_agent_core import CoreEventWriter, RunKernel

from app.services.agent_runner.paas_adapters import SaasEventLog

event_writer = CoreEventWriter(SaasEventLog(db), run_id=run_id)
kernel = RunKernel(
    llm_client=llm_client,
    event_writer=event_writer,
    tool_executor=tool_executor,
)
```

`rd-agent-core` 不 import `app.*`，也不 import SQLAlchemy/FastAPI/Redis/S3。数据库查询、租户权限、workspace lease、artifact 存储、SSE 投影继续留在 SaaS adapter 层。

## 业务 Agent 接入方式

PPT Agent、文档 Agent、数据分析 Agent 都应实现 `BusinessAgentAdapter`，而不是改 core：

- `build_prompt_sections()` 负责业务上下文；
- `list_tools()` 暴露业务工具；
- `build_verification_plan()` 声明验证策略；
- `extract_manifest()` 输出 artifact manifest。

因此 PPT 的 `deck_schema`、HTML 预览、PPTX 导出、视觉 QA 属于 PPT Agent；core 只认识通用 tool call、event、pause、usage、artifact manifest。

## 不做的事

- 不在 core 中硬编码 `ask_user`、PPT、HTML、SaaS route、数据库表名；
- 不让 core 跨库查询；
- 不在 core 里实现 provider router，`rd-llm-gateway` 作为注入的 `LLMClientPort` 后置接入；
- 不在 core 里投影前端 SSE 或操作 SaaS workspace lease，这些由 host adapter 负责；
- 不在当前切片删除 CodeSphere SaaS 的旧 engine loop，删除前需要发布包依赖与 golden trace 覆盖。
