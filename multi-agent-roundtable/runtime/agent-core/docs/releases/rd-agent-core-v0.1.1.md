# rd-agent-core v0.1.1

文档与 reference host 补强版本。

## 新增

- `docs/SDK-OVERVIEW.md`：SDK 定位、功能清单、架构分层和接入路线；
- `docs/API-REFERENCE.md`：公开接口文档；
- `docs/API-STABILITY.md`：0.x/1.x API 稳定性和弃用策略；
- `examples/reference_host`：SQLite-backed reference host；
- `examples/reference_host.demo`：可运行的 `RunKernel` 端到端示例；
- examples 测试进入默认 pytest suite。

## 兼容性

- `RunKernel` / `TurnKernel` 运行 API 无破坏性变化；
- `rd-agent-contracts` 仍为 `1.14.0`；
- `rd-llm-adapter` 仍为 `1.1.1`。

## 建议

新的接入方从 `docs/SDK-OVERVIEW.md`、`docs/QUICKSTART.md` 和 `examples/reference_host` 开始。

