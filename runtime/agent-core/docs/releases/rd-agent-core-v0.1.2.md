# rd-agent-core v0.1.2

SDK usability and release-hardening release.

## 新增

- `AgentRunner` lifecycle facade；
- `OpenAICompatLLMClient` 与 `AnthropicNativeLLMClient` reference implementation；
- `ProviderClientConfig`；
- `ToolSafetyPolicy`，支持 allowlist、blocklist、mutating tool confirmation；
- `docs/EVENT-PAYLOAD-SCHEMA.md`；
- release wheel install smoke；
- provider LLM client、AgentRunner、tool safety 单元测试。

## 兼容性

- `RunKernel` / `TurnKernel` 主路径兼容；
- `CoreToolPolicy` 新增 `safety_policy` 字段，默认行为保持允许；
- `rd-agent-contracts` 仍为 `1.14.0`；
- `rd-llm-adapter` 仍为 `1.1.1`。

## 建议

新接入方优先使用 `AgentRunner` 起步；需要精细事务控制的 host 继续直接使用 `RunKernel`。
