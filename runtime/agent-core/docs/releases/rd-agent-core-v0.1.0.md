# rd-agent-core v0.1.0

首个 early-release runtime kernel。

## 包含

- host-neutral `RunKernel` / `TurnKernel`；
- `CoreEventWriter` 和核心事件类型；
- `RunLimits`、重复工具调用保护、max tool calls 保护；
- `CoreToolPolicy` pause tool 语义；
- `rd_agent_core.testing` harness；
- host integration contract；
- release workflow 和 package tag。

## 搭配版本

- `rd-agent-contracts==1.14.0`
- `rd-llm-adapter==1.1.1`

## 说明

这个版本已经可用于受控早期接入，但文档和 reference host 在后续 `0.1.1` 中补齐。

