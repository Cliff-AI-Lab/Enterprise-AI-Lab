# Model Adapter 归一化层设计方案

> 历史设计记录：本文保留 model adapter 从 SaaS 抽离到 SDK 的演进细节。新的 host 接入应优先阅读 `docs/SDK-OVERVIEW.md`、`docs/API-REFERENCE.md` 和 `docs/QUICKSTART.md`；运行时主边界是 `rd-llm-adapter` + `rd-agent-core`，不是旧的 `rd-llm-gateway`。

**版本**：v42（fixture validator skipped gate）
**日期**：2026-04-30
**状态**：Phase 1A/1B 已实施；Phase 2A/2B/2C replay + 采样 + fixture 回归入口已实施；Anthropic native request/parser/transport PoC 已实施；adapter/transport registry 已落地；native runtime feature flag 和 adapter allowlist 已落地且默认关闭；native runtime 错误边界已补齐；Anthropic native usage 标准事件已补齐；recorded fixture active adapter 标记已修正；fixture validation CLI / runbook / versioned JSON report / adapter + model 覆盖统计与 gate / recorded + Anthropic scenario gate 已落地；recorded request 脱敏 gate 已落地；private recorded fixtures 已加入 `.gitignore`；validator 会拒绝空验证并支持 skipped gate；recorder 支持按模型 glob 定向采样；`.env.example` 已补默认关闭的 model adapter 配置；redacted thinking fixture 已补齐，待真实 SSE 样本补充
**作者**：shine + Claude，Codex review

---

## 版本历史

**v42 相对 v41 的关键变更**：

🟢 fixture validator skipped gate：
- `scripts/validate_model_adapter_fixtures.py` 新增 `--fail-on-skipped`。
- 灰度/发布前 job 可要求所有启用的 fixture 类别都必须有样本，避免目录配置错误时默默 skipped。

**v41 相对 v40 的关键变更**：

🟢 fixture validator report schema：
- JSON report 新增 `schema_version: 1`。
- JSON report 新增 `summary`，汇总 categories / checked / skipped / failures / raw_chunks，便于 CI / 灰度 job 直接消费。
- runbook 同步说明机器可读 report 结构。

**v40 相对 v39 的关键变更**：

🟢 private recorded fixture ignore：
- `.gitignore` 忽略 `tests/fixtures/recorded/model_adapter/*.jsonl*`，防止真实 recorded samples 被误提交。
- 新增 `tests/fixtures/recorded/model_adapter/.gitkeep` 保留默认 fixture 目录。
- runbook 同步说明真实样本只走内部临时存储或受控对象存储。

**v39 相对 v38 的关键变更**：

🟢 recorded request redaction gate：
- `scripts/validate_model_adapter_fixtures.py` 新增 `--require-recorded-redacted`，可强制检查 recorded request messages / tool arguments 已脱敏。
- recorder 现在会脱敏 request content blocks 里的 `input` 字段，避免 Anthropic native tool_use input 被写入 fixture。
- runbook 的 recorded fixture gate 示例加入脱敏检查。

**v38 相对 v37 的关键变更**：

🟢 fixture validator empty-run guard：
- `scripts/validate_model_adapter_fixtures.py` 现在拒绝同时传 `--skip-recorded` 和 `--skip-anthropic`。
- 空验证会作为参数错误退出，避免 CI / 灰度 job 没有实际检查却返回成功。

**v37 相对 v36 的关键变更**：

🟢 model adapter ENV example：
- `.env.example` 增加 native runtime rollout、recorded fixture sampling、fixture validator 目录相关 ENV。
- 示例值全部默认关闭或空值，避免部署模板误开启 native runtime 或真实流量录制。

**v36 相对 v35 的关键变更**：

🟢 recorded fixture scenario gate：
- `scripts/validate_model_adapter_fixtures.py` 会从 recorded fixture 的 expected events / legacy response 自动识别 `text`、`reasoning`、`tool_use`、`ask_user`、`usage`、`length`、`stop_reason:*` 等场景。
- 新增 `--require-recorded-scenario NAME`，可把 runbook 中 OpenAI-compatible replay 的场景覆盖要求变成可执行 gate。
- recorded validator 输出和 JSON report 现在也包含 `raw_chunks` / `scenarios`。

**v35 相对 v34 的关键变更**：

🟢 recorded sampling model filter：
- `MODEL_ADAPTER_RECORD_MODEL_PATTERNS` 支持逗号或分号分隔的 shell glob。
- recorder 会同时匹配 requested model 和 provider model，便于 saas-test 按 DeepSeek/Kimi/Claude/GPT 等模型族补齐 gate 样本。
- 未设置该 ENV 时保持全模型采样行为不变。

**v34 相对 v33 的关键变更**：

🟢 fixture validator JSON report：
- `scripts/validate_model_adapter_fixtures.py` 新增 `--json` 和 `--json-report PATH`。
- JSON report 包含 `ok/status/checked/failures/by_adapter_kind/by_model/raw_chunks/scenarios`，便于 CI 或 saas-test 灰度 job 读取。
- runbook 同步说明机器可读 report 输出。

**v33 相对 v32 的关键变更**：

🟢 recorded fixture model gate：
- `scripts/validate_model_adapter_fixtures.py` 现在按 `requested_model` / `provider_model_name` 统计 recorded fixtures。
- CLI 输出新增 `models=...`，并支持 `--require-recorded-model 'pattern=N'`，pattern 使用 shell glob 语义。
- runbook 的 recorded fixture 验证命令加入 DeepSeek / Kimi 模型族样本量 gate 示例。

**v32 相对 v31 的关键变更**：

🟢 redacted thinking fixture：
- 新增 `tests/fixtures/anthropic_native/redacted_thinking.json`，覆盖 Anthropic `redacted_thinking` request roundtrip 和 stream replay。
- 仓库内合成 fixtures 现在覆盖 `signed_thinking`、`redacted_thinking`、`tool_use`、`tool_result`、`usage`、`stop_reason` 场景。

**v31 相对 v30 的关键变更**：

🟢 Anthropic fixture scenario gate：
- `scripts/validate_model_adapter_fixtures.py` 会从 Anthropic native fixture 自动识别 `signed_thinking`、`redacted_thinking`、`tool_use`、`tool_result`、`usage`、`stop_reason`。
- 新增 `--require-anthropic-scenario NAME`，可把 runbook 里的 Anthropic 场景覆盖要求变成可执行 gate。
- CLI 输出新增 `scenarios=...`，便于灰度前确认真实样本覆盖范围。

**v30 相对 v29 的关键变更**：

🟢 Anthropic fixture chunk gate：
- `scripts/validate_model_adapter_fixtures.py` 新增 `--require-anthropic-chunks N`。
- validator 会统计 Anthropic native fixture 的 `stream.raw_chunks` 总数，并在输出中显示 `raw_chunks=N`。
- runbook 的 Anthropic native 验证命令加入 `--require-anthropic-chunks 100`，让真实 SSE 样本门槛可执行。

**v29 相对 v28 的关键变更**：

🟢 native runtime adapter allowlist：
- 新增 `MODEL_ADAPTER_NATIVE_RUNTIME_ADAPTERS`，可用逗号分隔 adapter kind 限制 native runtime rollout 范围。
- `MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME=1` 且 allowlist 未设置时保持允许所有已实现 native runtime；灰度建议设置为 `anthropic_native`。
- allowlist 不包含的 native adapter 会 fallback 到 `openai_compat`，避免未完成 adapter 被总开关误触发。

**v28 相对 v27 的关键变更**：

🟢 recorded fixture active adapter 标记：
- `record_turn_if_enabled()` 现在接收 active `adapter_kind`，并写入 `profile_snapshot.adapter_kind`。
- 当配置为 native 但 `MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME` 未开启而 fallback 到 `openai_compat` 时，recorded fixture 会标记为 `openai_compat`，避免 validator 后续用错 parser。

**v27 相对 v26 的关键变更**：

🟢 Anthropic native usage 标准事件：
- `AnthropicNativeParserSession.feed()` 在 `message_start` / `message_delta` 收到 usage 时会 yield `UsageUpdate`。
- 最终 `TurnDone.usage` 仍保留合并后的 usage；legacy stream delta 不受影响，因为 `UsageUpdate` 不会映射成旧前端 delta。

**v26 相对 v25 的关键变更**：

🟢 recorded fixture adapter gate：
- `scripts/validate_model_adapter_fixtures.py` 新增 `--require-recorded-adapter KIND=N`。
- 灰度/CI 可强制要求某个 adapter kind 至少有 N 个 recorded samples，不满足时 validator 退出非 0。
- runbook 的 recorded fixture 验证命令加入 `--require-recorded-adapter openai_compat=50` 示例。

**v25 相对 v24 的关键变更**：

🟢 recorded fixture adapter 覆盖统计：
- `scripts/validate_model_adapter_fixtures.py` 在验证 recorded fixtures 时按 `profile_snapshot.adapter_kind` 统计数量。
- CLI 输出新增 `adapters=openai_compat:N,anthropic_native:M` 后缀，方便 saas-test 采样后确认样本覆盖了哪些 adapter runtime。
- runbook 同步说明 adapter 覆盖统计的含义。

**v24 相对 v23 的关键变更**：

🟢 native runtime 错误边界补齐：
- `claude_client.create_streaming_turn()` 的 try 范围前移，覆盖 adapter/transport resolve 和 request build。
- adapter 未实现、transport 未实现、native request build 协议错误统一包装成不可重试的 `MODEL_PROTOCOL_ERROR`，避免开启测试 flag 后裸异常越过 engine retry 边界。
- 异常发生在 parser session 创建前时，`partial_output=False`，不调用 `finalize_on_error()`。

**v23 相对 v22 的关键变更**：

🟢 native runtime feature flag 落地：
- `claude_client.create_streaming_turn()` 现在通过 registry 解析 active adapter/transport。
- 默认仍强制 `openai_compat`，保持现有网关运行路径；只有 `MODEL_ADAPTER_ENABLE_NATIVE_RUNTIME=1` 时才允许 `profile.adapter_kind` 切到 `anthropic_native` 等 native runtime。
- recorded fixture validator 改为按 `profile_snapshot.adapter_kind` 选择 parser；旧样本没有该字段时继续按 `openai_compat` 回放。
- 运行路径切换仍需真实 fixtures gate 后才能在测试环境开启。

**v22 相对 v21 的关键变更**：

🟢 adapter transport registry 落地：
- `model_adapter.registry` 现在同时解析 adapter 和 transport，`openai_compat` / `anthropic_native` 的 request/parser 与 transport 映射集中在同一处。
- 新增 `resolve_transport()` / `resolve_transport_for_profile()` / `supported_transport_kinds()` 和 `TransportNotSupportedError`。
- 仍未把 Anthropic native 接入 `claude_client.py` 主链路；运行路径切换继续等待真实 fixtures gate。

**v21 相对 v20 的关键变更**：

🟢 fixture validation runbook 落地：
- 新增 `docs/runbooks/MODEL_ADAPTER_FIXTURES.md`，明确 `saas-test` 采样 ENV、validator 命令、隐私约束、失败处理和推进 gate。
- 设计文档继续保留机制说明；实际执行步骤以 runbook 为准。

**v20 相对 v19 的关键变更**：

🟢 fixture validation CLI 离线执行修正：
- `app/services/agent_runner/__init__.py` 改为懒加载核心导出，避免仅导入 `model_adapter` 就触发 `claude_client -> model_profile -> app.models -> ENCRYPTION_KEY`。
- `scripts/validate_model_adapter_fixtures.py` 现在可在没有业务 `.env` / `ENCRYPTION_KEY` 的离线环境执行。

**v19 相对 v18 的关键变更**：

🟢 fixture validation CLI 落地：
- 新增 `scripts/validate_model_adapter_fixtures.py`，统一校验 recorded OpenAI-compatible fixtures 和 Anthropic native request/SSE fixtures。
- 支持 `--recorded-dir`、`--anthropic-dir`、`--require-recorded`、`--require-anthropic`、`--skip-*`。
- 目录不存在或无样本时默认 skip；灰度/CI 可用 `--require-*` 强制要求样本存在。
- 复用 `StreamRecorder.diff_against_legacy()` 和 Anthropic snapshot 校验逻辑，方便 saas-test 采样后直接跑。

**v18 相对 v17 的关键变更**：

🟢 Anthropic native transport PoC 落地：
- 新增 `app/services/agent_runner/model_adapter/anthropic_transport.py`。
- transport 按 Anthropic Messages API 形态发 `POST /v1/messages`，带 `x-api-key`、`anthropic-version: 2023-06-01`、`content-type: application/json`、`accept: text/event-stream`。
- 新增 SSE `event:` / `data:` 行解析工具，支持 keepalive 注释、多行 data、末尾无空行 flush、`[DONE]` 忽略。
- 仍未接 `claude_client.py` 主链路；真实接入前需用 `ANTHROPIC_NATIVE_FIXTURES_DIR` 跑真实 SSE 样本。

**v17 相对 v16 的关键变更**：

🟢 Anthropic native capabilities 派生落地：
- `resolve_capabilities()` 对 `sdk_type=anthropic/anthropic_native` 派生 `thinking.mode=anthropic_block`。
- Anthropic thinking 默认 `has_signature=True`、`must_roundtrip=True`，并支持 `thinking_budget_tokens` override。
- Anthropic native 默认 `tool_call_style=anthropic_blocks`。
- Anthropic prompt caching 能力派生为 `supports_prompt_caching=True`、`prompt_caching_style=anthropic_marker`（可由 override 关闭）。

**v16 相对 v15 的关键变更**：

🟢 adapter registry PoC 落地：
- 新增 `app/services/agent_runner/model_adapter/registry.py`，集中解析 `adapter_kind -> adapter instance`。
- 当前明确支持 `openai_compat` 和 `anthropic_native`；`openai_responses/gemini_native` 等尚未实现时会早失败。
- registry 仍未接 `claude_client.py` 主链路；当前运行路径继续走 OpenAI compat shim。

**v15 相对 v14 的关键变更**：

🟢 Anthropic native fixture 回归入口落地：
- 新增 `tests/test_model_adapter_anthropic_fixtures.py`，支持 request snapshot 和 SSE stream snapshot。
- 默认读取 `tests/fixtures/anthropic_native/*.json`，也可用 `ANTHROPIC_NATIVE_FIXTURES_DIR` 指向外部真实样本目录。
- 新增合成 fixture `signed_thinking_tool_use.json`，覆盖 signed thinking、text、tool_use、tool_result、usage、stop_reason。
- 后续把真实 Anthropic request/SSE 样本按同一 JSON 结构放入目录即可进入回归。

**v14 相对 v13 的关键变更**：

🟢 reasoning metadata 能力补齐：
- 新增 `reasoning_metadata_from_blocks()`，支持从完整 reasoning blocks 写 metadata。
- `reasoning_blocks` 现在可保留 `signature/redacted/data`，为 Anthropic native thinking 回传做准备。
- legacy `reasoning_content` 仍只写可见非 redacted 文本，避免把 encrypted/redacted data 展示到旧路径。
- 现有 executor/project_service 仍走 `reasoning_metadata_from_text()`；native 接入时再切到完整 blocks 写入。

**v13 相对 v12 的关键变更**：

🟢 Anthropic native request builder PoC 落地：
- `AnthropicNativeAdapter.build_request()` 已能把现有 legacy message/tool schema 映射成 Anthropic native body。
- 支持 system text、user/assistant text、assistant `tool_use`、user `tool_result`、tool schema、thinking budget。
- 支持带 `signature` 的 `reasoning_blocks` 输出为 Anthropic `thinking` block，支持 redacted reasoning 输出为 `redacted_thinking`。
- 明确拒绝 legacy `reasoning_content` 或无 signature 的 `reasoning_blocks`，避免 native Anthropic 回传 thinking 时丢 signature 后上线触发 400。
- 仍未接入 transport/engine；下一步需要真实 Anthropic SSE/request fixtures 做 replay 和 request snapshot 验证。

**v12 相对 v11 的关键变更**：

🟢 Anthropic native parser PoC 落地：
- 新增 `app/services/agent_runner/model_adapter/anthropic_native.py`，实现不接主链路的 `AnthropicNativeParserSession`。
- 覆盖 `message_start` usage、`content_block_delta` text/thinking/input_json、`signature_delta`、`redacted_thinking`、`message_delta.stop_reason`、`message_stop`。
- `thinking` signature 会进入 `ReasoningBlock.signature`，`redacted_thinking.data` 原样进入 `ReasoningBlock.data`。
- 新增 `tests/test_model_adapter_anthropic_native.py`，用 fake Anthropic SSE dict 锁住 text/thinking/signature/redacted/tool_use/invalid_json/error 行为。
- 仍未接入 registry / transport / engine；下一步需要用真实 Anthropic SSE fixtures 跑 replay，再决定是否接运行路径。

**v11 相对 v10 的关键变更**：

🟢 Phase 2C 落地：
- 新增 `tests/test_model_adapter_recorded_fixtures.py`，可把采样得到的 `*.jsonl(.gz)` fixtures 直接纳入 replay/diff 回归。
- 默认扫描 `tests/fixtures/recorded/model_adapter`，也可用 `MODEL_ADAPTER_RECORDED_FIXTURES_DIR` 指定目录。
- 没有 fixtures 时测试 skip，不影响普通 CI；有 fixtures 时任何 legacy event/response diff 都会失败。

**v10 相对 v9 的关键变更**：

🟢 Phase 2B 落地：
- `claude_client.create_streaming_turn()` 成功完成时可按 ENV gate 写 `RecordedTurn` fixture，不改变返回 dict 或 stream event。
- 默认关闭：`MODEL_ADAPTER_RECORD_TURNS=1` 才启用。
- 支持 `MODEL_ADAPTER_RECORD_DIR`、`MODEL_ADAPTER_RECORD_SAMPLE_RATE`、`MODEL_ADAPTER_RECORD_INCLUDE_MESSAGES`。
- 默认 scrub `request_body.messages[*].content` 和 tool call arguments；raw chunks / expected legacy 输出仍保留，用于 replay diff。
- recorder 写盘异常只打 warning，不影响 LLM 主链路。

**v9 相对 v8 的关键变更**：

🟢 Phase 2A 落地：
- 新增 `app/services/agent_runner/model_adapter/recorder.py`，提供 `RecordedTurn` / `StreamRecorder`。
- 支持单 turn raw chunks 录制为 gzip jsonl、加载、通过 adapter replay、按 raw chunk 边界生成 legacy stream events、对比 `expected_events` 和 `expected_legacy_dict`。
- `profile_snapshot` 写盘前自动脱敏 `api_key/authorization/access_token/secret/password` 等字段。
- 新增 `tests/test_model_adapter_recorder.py` 覆盖录制加载、脱敏、replay 和 diff。
- 生产 ENV-gated 采样接入仍留在 Phase 2B；本阶段不改 LLM 运行主链路。

**v8 相对 v7 的关键变更**：

🟢 Phase 1B 落地：
- `ResolvedModelProfile` 已向后兼容追加 `adapter_kind/capabilities/protocol_limits`，旧字段继续保留给 `engine.py` / `claude_client.py` 读取。
- 新增 `resolve_adapter_kind()` / `resolve_capabilities()`，从现有 flat profile 字段和 `channel.models[model]` overrides 在内存里派生能力，不改 DB schema。
- assistant reasoning metadata 已双写：旧 `reasoning_content` + 新 `reasoning_blocks`；恢复时优先读 `reasoning_blocks`，fallback 到旧字段。
- 新增 L3 engine golden tests：monkeypatch LLM 边界，锁定 reasoning/tool_use/tool_result/final text 主路径、transport 异常闭合、`length` 续写累计终态、`length_limit` 闭合、`ask_user` 暂停合约、空响应重试、`max_turns` 合成收尾、partial stream 重发整轮。
- `engine_state_json` 仍保持不动，符合阶段 1 约束。

**v7 相对 v6 的关键变更**（源于 Codex 第六轮 review + selfagency 复核）：

🔴 P0 修复：
- **`ResolvedModelProfile` 明确为扩展而非替换**：阶段 1A 保留现有 `sdk_type/context_window/supports_function_calling/supports_stream_usage/tool_call_style` 等字段，只追加 `adapter_kind/capabilities/protocol_limits`；否则 `engine.py` / `claude_client.py` 会被打断。
- **阶段 1 拆成 Phase 1A / 1B**：1A 只做 OpenAI compat shim + characterization tests，`engine.py` 不动；1B 再做 capabilities 派生和 DB reasoning_blocks 双读双写。
- **OpenAI compat tool name 行为锁定旧实现**：streaming delta 里的 `function.name` 采用赋值语义，不拼接，避免兼容网关重复发完整 name 时变成 `searchsearch`。
- **UsageUpdate 不引用不存在字段**：阶段 1A 只使用当前 `UsageRecord(input_tokens/output_tokens/total_tokens)`，`cached_input_tokens/reasoning_tokens` 等到 usage 模型扩展后再接。

🟡 P1 修复：
- 异常路径统一：`finalize_on_error()` 不 yield `TurnDone`，不发终态 text/reasoning/tool_use；已发出的 delta 保留，最终 lifecycle 只由 engine 闭合。
- selfagency 借鉴范围收紧：吸收 normalizer test matrix、index-based tool accumulator、thinking tag parser、资源限制思路；不吸收扁平 `StreamChunk`、silent drop、JSON repair。

**v6 相对 v5 的关键变更**（源于 Codex 第五轮 review）：

🔴 P0 修复：
- **shim exception 闭合移到 engine 层**：v5 在 `create_streaming_turn` shim 内部直接 emit `assistant_turn_ended` 是错的——engine 才拥有 `turn_id/message_id`，shim 这么做会导致 retry 时同 turn 重复闭合。v6 shim 只 raise exception，engine 层 catch 后做 lifecycle event 收尾。
- **`OpenAICompatParserSession` 完整规格**：v5 只有三行占位符。v6 补完整状态机伪代码：等价复刻 `claude_client.py:213-300` 的所有 legacy 行为（usage-only chunk / model_extra.reasoning_content / tool delta 心跳 / id 后到等）。
- **`ToolCallArgsDelta` 加 `index` 字段**：id 未到 args 已到时事件无法可靠归属。v6 用 `index` 作为 session 内主键。
- **`resolve_capabilities` 字段映射对齐真实代码**：v5 写错字段名。v6 严格对应 `model_profile.py:24-33` 的真实字段（`supports_function_calling` / `tool_call_style="native"` 等）。

🟡 P1 修复：
- §4.1.1 状态机 accumulator 补 `data` 字段（v5 实现里有，规格没同步）
- `StreamParserSession` Protocol 加 `finalize_on_error()` 声明（v5 调用了但接口没声明）
- ProtocolLimits 超限和 transport exception 区分 `reason="protocol_limit"` vs `"error"`
- redacted data 缺失从 `continue` 静默改成 `raise InvariantError`（避免 silent skip）
- `tool_call_style` 值域和真实 profile 对齐（`"native"` 而非 `"openai_native"`）

🔵 范围调整：
- **Anthropic native adapter 伪代码降级为"阶段 2 PoC 草图"**：阶段 1 不承诺，130 行实现细节会让 review 注意力偏离 OpenAI compat shim
- **新增 §11.5 异常路径时序图**：transport exception → engine catch → emit assistant_turn_ended → retry 决策的完整流程
- **新增 §11.6 OpenAI compat → legacy event 映射表**：StandardEvent → 现 SSE 事件的逐项映射

**v5 相对 v4 的关键变更**（源于 Codex 第四轮 review）：

🔴 P0 修复（含架构级）：
- **parser 接口重新设计**：`parse_stream_chunks(iter([raw_chunk]))` per-chunk 调用方式会丢跨 chunk 状态。v5 改成 **stateful `StreamParserSession`**，整个 turn 一个实例，按 `feed(chunk)` 增量推送，session 内部维护状态。这是 v1-v4 都犯的隐蔽错。
- **redacted_thinking `data` 字段贯穿全链路**：v4 类型加了 `data` 但 accumulator / TurnDone 聚合 / build_request 三处伪代码仍按 `thinking` 输出。v5 全部修对。
- **transport exception 闭合语义明确**：失败 attempt 是否 emit `assistant_turn_ended`、前端是否看到重复 delta 全部写明。
- **ProtocolLimits 超限信号统一**：`adapter 不能伪造 ErrorEvent` vs `超限上抛 ErrorEvent` 的矛盾——v5 选定**超限抛 transport-level exception**，不进 StandardEvent。

🟡 P1 修复：
- `ToolCallStart.call_id` 改可选 + 新增 `ToolCallIdDelta`（OpenAI streaming id 也可能后到）
- `InvalidToolCall` 加入 `StandardContentBlock` union（`TurnDone.content` 主真相源能保留 invalid 顺序）
- `resolve_capabilities` 字段映射表对齐真实 `model_profile.py` 字段名（`supports_function_calling` → `supports_tool_use` 显式映射）
- `TextDelta` 加 `block_index`（多 text block 与 thinking/tool 交错时的边界）

🔵 一致性修复：
- 附录 A "4 处 → 2 处" 表述更正（仍是 4 处，但全在 adapter + DB 兼容层，不再分散到 engine）

**v4 相对 v3 的关键变更**（源于 Codex 第三轮全面 review）：

🔴 P0 修复：
- **`TurnDone` 加 `content: list[StandardContentBlock]` 作为主真相源**——v1/v2/v3 都犯的错：分组聚合（text_blocks / reasoning_blocks / tool_calls）天生丢失 Anthropic 的 thinking → text → tool_use → text 交错顺序。content 是真相，分组只是 view。
- **`ReasoningBlock.data` 字段（仅 redacted）**——Anthropic 真实协议 redacted_thinking 用 `data: str` 字段（加密 blob）而非 `thinking: str`。v3 状态机写错。
- **阶段 1 shim 单切点**——v3 同时说 Step 1.3 在 `create_streaming_turn` 里 shim 又说 Step 1.4 在 `_call_llm_with_retries` 切到 StandardEvent，会导致两边各写一半。v4 锁定：仅 `create_streaming_turn` 内部接 adapter，`_call_llm_with_retries` 阶段 1 不动控制流。

🟡 P1 修复：
- partial retry 残余矛盾扫尾：§5.2 伪代码、§8 #13 全部对齐"阶段 1 闭合状态并重发整轮，partial 仅记录"
- Anthropic tool_use 状态机伪代码补齐 `block_index → call_id` 映射，不再有 `call_id="?"`
- `ToolCallStart.name` 改为可选（OpenAI streaming id 先到、name 后到）；终态 `StandardToolCall.name` 必填
- `ThinkingExtractionConfig.must_roundtrip` 默认 False（v3 默认 True 反了）
- `ProtocolLimits` 补 `max_json_keys`、`max_total_stream_bytes`；transport vs adapter 执行边界明确
- 消息层：`StandardMessage.content` 是唯一主真相源，删 `reasoning_blocks` 顶层字段（保留 legacy `reasoning_text` 阶段 1 兼容）
- `stop_reason` 标准协议统一 `"tool_use"`，legacy `"tool_calls"` 仅在兼容层映射
- 新增 §11 capabilities 迁移规则：从现 `model_channels` flat 字段构造 `ModelCapabilities` 的兼容函数

🔵 一致性修复：
- `metadata_json` 字段名统一：标准 `reasoning_blocks` + legacy `reasoning_content`，不再混用
- `ToolCallEnd` 携带终态完整信息（`name / index / encoding / raw_args`），InvalidToolCall 由它派生
- §8 风险表 #13 删"Anthropic streaming resume"幻想，改"无原生续传"
- §10 Q10 与 §8 #7 #13 全部对齐
- v3 历史记录里"可启动阶段 1"改成"补齐 v4 边界后可启动"

**v3 相对 v2 的关键变更**（源于 Codex 第二轮 review + selfagency/llm-stream-parser 项目分析）：
- 🔴 **P0**：修 partial retry 语义文档矛盾（§8 风险表 #7 与 §10 Q10 互相冲突）
- 🔴 **P0**：Anthropic thinking 状态机重写——`signature_delta` 是独立 SSE 事件而非 `thinking_delta.provider_data`
- ✅ **P1**：`encoding` 字段加到 `StandardToolCall` 终态（主真相源）+ `ToolCallStart.encoding_hint`（可选诊断）
- ✅ **P1**：`thinking_extraction` 从 capabilities 平铺改成 sub-schema（含 mode / open_tag / close_tag / has_signature / must_roundtrip）
- ✅ **P1**：协议层资源限制独立成 `ProtocolLimits` + Profile 业务策略分层
- ✅ **P1**：新增"阶段 1 工具：StreamRecorder & Event Replay"章节
- ✅ **P1**：阶段 1 范围明确收窄到"OpenAI compat shim + characterization tests"，阶段 2 启动门槛加 Anthropic thinking 状态机 PoC
- ✅ **P2**：吸收 selfagency 的"流式 XML parser + nesting depth 限制"机制（用于 XML thinking tags + XML tool calls）
- ✅ **P2**：明确 selfagency 哪些不吸收（auto-repair JSON / context dedup / 隐私 scrub 标签策略）

**v2 相对 v1 的关键变更**（源于 Codex 第一轮 review）：
- ✅ **P0**：`reasoning: str` → `reasoning_blocks: list[ReasoningBlock]`（支持 Anthropic thinking signature/redacted）
- ✅ **P0**：`ModelCapabilities` 从 Adapter 类下沉到 `ResolvedModelProfile`（同 adapter 下不同模型差异仍能表达）
- ✅ **P0**：DB 持久化分两层 `MessageView` + `ConversationState`，阶段 1 不动 `engine_state_json`
- ✅ **P1**：补齐协议成员 `StandardToolCall / InvalidToolCall / ProviderState / Source / ErrorEvent`
- ✅ **P1**：Adapter 接口拆成 `build_request()` + `parse_stream_chunks()`，transport 不下沉到 adapter
- ✅ **P1**：阶段 1 engine 改造采用 shim 模式（不拆文件），先锁行为再换边界
- ✅ **P1**：content block 补 `image / file / source / cache_control`，或明确标记 phase 1 非目标
- ✅ **P2**：风险表补齐 partial_output 重试、lease mid-turn 过期、tool args JSON 解析失败、事件顺序约束
- ✅ 评审问题清单新增 4 个关键问题：协议无损性、provider_state 位置、capabilities 归属、partial stream 语义
- ✅ 新增"阶段 1 characterization test 矩阵"章节，3 层测试覆盖

---

## 1. 背景与动机

### 1.1 现状

CodeSphere 的 agent_runner 目前**没有统一的模型适配层**。所有模型（DeepSeek / Kimi / Claude / GPT / Gemini / GLM）都假设走 **OpenAI Chat Completions 兼容协议**，通过 `http://localhost:8083/v1` 的 CLIProxyAPI 网关抹平协议差异。

相关文件：
- `app/services/agent_runner/claude_client.py`（432 行）：唯一的 LLM 调用路径
- `app/services/agent_runner/model_profile.py`（180 行）：运行时 profile 解析
- `app/services/agent_runner/engine.py`（1579 行）：主循环，消费 LLM 响应
- `app/services/workspace_support/llm/`：**死代码**，LLMFactory + 5 个 client，无任何调用点

### 1.2 痛点

**2026-04-24 DeepSeek `reasoning_content` 事件**暴露架构问题。修复涉及 4 处代码修改：

| # | 位置 | 修改内容 | 该不该在这里 |
|---|------|---------|------------|
| 1 | `claude_client.py:244` | 从 `delta.model_extra.reasoning_content` 读思维链 | ✅ 传输层合理 |
| 2 | `claude_client.py:_build_oai_messages` | 构造请求时把 reasoning_content 塞回 | ⚠️ 应在独立翻译层 |
| 3 | `engine.py` ask_user / closing | 合成 assistant 消息时手动挂 reasoning_content | ❌ engine 不该知道 |
| 4 | `project.py` + `project_service.py` | 持久化 + 恢复时带 reasoning_content | ❌ 持久层不该知道 |

**本质**：单一模型的语义差异（DeepSeek thinking 要求回传）**泄漏到了 engine 和 DB 层**。

### 1.3 业务诉求

> 平台后续肯定主流模型都要接入。—— 产品方向

- **短期**：Claude 4 系列、GPT-5 系列
- **中期**：Gemini 原生、豆包、通义
- **长期**：多 provider 直连（绕过网关），用上 prompt caching、原生 tool use 等能力

### 1.4 目标

建立**归一化中间层**，让上层代码（engine / DB / UI）**永远不需要**知道具体模型。接新模型收敛到"加一个 Adapter 类 + 配置渠道"。

---

## 2. 设计原则

1. **模型差异只能存在于 Adapter + Profile 内部**。engine / DB / UI 看到的只有标准事件/消息。
2. **协议必须无损**。不能把 provider-specific 的关键信息（thinking signature、grounding sources、response id）压成字符串丢失。宁可留 opaque `provider_state` 字段也不要丢。
3. **能力声明与协议翻译分离**。
   - Adapter 负责"协议族怎么翻译"（openai_compat / anthropic_native / gemini_native）
   - Profile 负责"具体这个模型有什么特性"（thinking_must_roundtrip / max_context / cache_support）
4. **双向翻译独立可测**。
   - 入站：原始 chunks → StandardEvent
   - 出站：StandardMessage → provider 请求体
   - HTTP transport 和 SDK 封装在更外层，adapter 是纯函数边界
5. **先锁行为，再扩能力**。阶段 1 只做重构，characterization test 保证 0 行为变化。
6. **不提前抽象**。第 4 个模型来了再加新协议维度。

---

## 3. 架构总览

### 3.1 当前架构

```
[LLM Provider]
    ↓
[CLIProxyAPI 网关 localhost:8083]      ← 协议归一化（都转成 OpenAI 格式）
    ↓
[claude_client.py]                     ← 硬写死假设 OpenAI 格式
    ↓ 特判 reasoning_content / kimi extra ...
    ↓
[engine.py]                             ← 主循环 + 工具调度（1579 行）
    ↓ 发 SSE events
    ↓
[tool_builder → SSE]                   ← 已有事件翻译层
    ↓
[前端 V2 状态机]                        ← UI 投影
```

### 3.2 目标架构

```
[LLM Provider: Anthropic / OpenAI / Gemini / DeepSeek / ...]
    ↓
[可选：CLIProxyAPI 网关 或 直连]        ← 协议层
    ↓
┌─────────────────────────────────────────────────────────┐
│ ModelAdapter 归一化层（新增）                            │
│                                                          │
│ Pure translation functions:                              │
│  • build_request(messages, tools, profile) → dict        │
│  • parse_stream_chunks(chunks) → Iterator[StandardEvent] │
│                                                          │
│ Transport 不在 adapter 里，由 engine/runner 管理         │
└─────────────────────────────────────────────────────────┘
    ↓ 标准事件流（TextDelta/ReasoningDelta/ToolCall*/...）
    ↓ 标准消息（StandardMessage + reasoning_blocks + provider_state）
[engine.py]                             ← 不感知模型
    ↓
[持久化分两层：MessageView + ConversationState]
    ↓
[tool_builder → SSE]                    ← 事件协议独立演进
    ↓
[前端 V2 状态机]
```

---

## 4. 标准协议设计

### 4.1 标准流式事件

```python
# agent_runner/model_adapter/events.py
from dataclasses import dataclass, field
from typing import Literal, Any

@dataclass(frozen=True)
class TextDelta:
    """用户可见的 chat 文本增量。

    v5 修正：加 `block_index` 字段。Anthropic 一个消息里可能有多个 text block
    （比如 thinking → tool_use → text → tool_use → text 这种交错），中间事件
    流必须能区分属于哪个 text block，否则 consumer 拼不出正确顺序。
    OpenAI compat 协议里通常只有一个 text block，默认 0 即可。
    """
    text: str
    block_index: int = 0

@dataclass(frozen=True)
class ReasoningDelta:
    """思维链文本增量。仅承载文本片段，不承载 signature/redacted 等元数据。"""
    text: str
    block_index: int = 0  # 多段 reasoning（Anthropic 可能 tool 前后各一段）的边界
    provider_data: dict | None = None  # 文本相关的次要元数据；signature 不放这里

@dataclass(frozen=True)
class ReasoningSignature:
    """Anthropic thinking 的 signature 增量。

    重要：Anthropic SSE 协议里 `signature_delta` 是**独立的 content_block_delta**，
    不是 `thinking_delta` 的子字段。adapter 必须按 SSE 顺序 yield 这个事件。
    引用：https://docs.anthropic.com/en/api/messages-streaming
    """
    block_index: int
    signature: str  # 完整 signature（Anthropic 一次给完，非分片）

@dataclass(frozen=True)
class ReasoningBlockEnd:
    """一个 reasoning block 结束（Anthropic content_block_stop 触发）。

    收到这个事件 adapter/engine 应把累积的 ReasoningDelta + ReasoningSignature
    封装为一个完整的 ReasoningBlock（含可选 signature）。
    """
    block_index: int
    redacted: bool = False  # Anthropic redacted_thinking 块在 stop 时标记

@dataclass(frozen=True)
class ToolCallStart:
    """tool call 开始事件。

    v5 修正：call_id 和 name 都是可选——OpenAI streaming delta 可能先给 index，
    id/name 都后到。consumer 应该用 index 作为 session 内部 key 跟踪；
    必填的不变量都在终态 StandardToolCall 上保证。
    """
    index: int  # 并行 tool_calls 的位置（必填，session 内主键）
    call_id: str | None = None           # OpenAI streaming 可能后到，等 ToolCallIdDelta
    name: str | None = None              # OpenAI streaming 可能后到，等 ToolCallNameDelta
    encoding_hint: Literal["native_json", "xml_bare", "xml_json_wrapped"] | None = None

@dataclass(frozen=True)
class ToolCallIdDelta:
    """OpenAI streaming：id 在 ToolCallStart 后才到达的补充事件"""
    index: int
    call_id: str

@dataclass(frozen=True)
class ToolCallNameDelta:
    """OpenAI streaming：name 在 ToolCallStart 后才到达的补充事件"""
    index: int
    name_delta: str

@dataclass(frozen=True)
class ToolCallArgsDelta:
    """v6 修正：必须带 index，call_id 改可选——OpenAI streaming 中 id 可能晚于
    args 到达，consumer 用 index 作为 session 内主键归属 args delta 到正确 tool。
    """
    index: int                # 必填，session 内主键
    delta: str                # JSON 片段（不在中间做 parse，统一在 ToolCallEnd 解析）
    call_id: str | None = None  # 可选；id 已知时填，便于诊断

@dataclass(frozen=True)
class ToolCallEnd:
    """tool call 结束事件。携带终态完整信息，让 InvalidToolCall 可以从这里派生。

    v4 补字段（解决 ToolCallEnd 信息不足）：
    - name / index / encoding：流式期间累积出的终态值
    - raw_args：完整的原始 JSON 字符串（无论 parse 成功失败都保留）
    - parsed_input：parse 成功时填，失败时为 None
    - parse_error：parse 失败时填
    """
    call_id: str
    name: str
    index: int
    encoding: Literal["native_json", "xml_bare", "xml_json_wrapped"]
    raw_args: str                            # 原始字符串，诊断+重放用
    parsed_input: dict | None                # 成功解析的完整 input
    parse_error: str | None                  # 解析失败时的错误

@dataclass(frozen=True)
class UsageUpdate:
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0  # OpenAI Responses / Anthropic thinking 单独计数

@dataclass(frozen=True)
class Source:
    """grounding / citation 来源（Gemini Search, Anthropic citations）"""
    url: str | None = None
    title: str | None = None
    snippet: str | None = None
    provider_data: dict | None = None

@dataclass(frozen=True)
class SourceAdded:
    sources: list[Source]

@dataclass(frozen=True)
class ErrorEvent:
    """流式过程中的软错误（非致命，由 stream 内部 chunk 携带）。

    **责任边界**（v4 明确）：
    - `ErrorEvent` 仅承载 stream 内部的错误 chunk（如 OpenAI compat 上游返回 ErrorChunk）
    - HTTP 4xx/5xx/超时/连接失败由 **transport 层抛 exception**，不变成 StandardEvent
    - engine 在 transport exception 和 ErrorEvent 上分别做处理（前者 raise，后者通过 yield 来）
    - adapter 不能"伪造" ErrorEvent，只能从原生 chunk 转换
    """
    code: str              # "RATE_LIMITED" / "CONTENT_FILTER" / ...
    message: str
    retryable: bool
    partial: bool          # 已有部分 output（阶段 1 仅打点，不参与控制流）

@dataclass(frozen=True)
class TurnDone:
    """本轮结束的聚合（流的最后一个事件）。

    主真相源是 content（保留 Anthropic thinking → text → tool_use → text 交错顺序）。
    text_blocks / reasoning_blocks / tool_calls 是 convenience view，**从 content 派生**，
    不能作为持久化或回传的真相源。
    """
    stop_reason: Literal["stop", "tool_use", "length", "content_filter", "error", "ask_user"]
    # 主真相源：保留原始顺序的 content blocks
    content: list["StandardContentBlock"]
    # convenience views（从 content 派生，方便消费方）
    text_blocks: list["TextBlock"]
    reasoning_blocks: list["ReasoningBlock"]
    tool_calls: list["StandardToolCall"]   # encoding 已在终态确定
    invalid_tool_calls: list["InvalidToolCall"]
    sources: list[Source]
    usage: UsageUpdate
    provider_state: "ProviderState | None" # opaque，原样持久化+回传
    raw_stop_reason: str                   # 原始 provider 字段，诊断用

StandardEvent = (TextDelta | ReasoningDelta | ReasoningSignature | ReasoningBlockEnd
                 | ToolCallStart | ToolCallIdDelta | ToolCallNameDelta
                 | ToolCallArgsDelta | ToolCallEnd
                 | UsageUpdate | SourceAdded | ErrorEvent | TurnDone)
```

**设计要点**（v2/v3 反馈吸收）：
- **Reasoning 三事件而非一事件**（v3 修正）：`ReasoningDelta`（文本）+ `ReasoningSignature`（签名，独立事件）+ `ReasoningBlockEnd`（块结束 + redacted 标记）。这才能正确映射 Anthropic SSE 的 `thinking_delta` / `signature_delta` / `content_block_stop`。v2 把 signature 塞 ReasoningDelta.provider_data 是错的。
- `ToolCallStart.encoding_hint` 是诊断用的初步判断，**真相在 `StandardToolCall.encoding` 终态字段**（XML bare vs json-wrapped 必须解析完才能定）。
- `ToolCallEnd.parse_error`：tool args JSON 解析失败的落点（仅在 `ToolCallEnd` 上做 JSON 解析，中间 `ToolCallArgsDelta` 不解析，避免无谓失败累积）。
- `SourceAdded`：Gemini grounding sources / Anthropic citations 的落点。
- `ErrorEvent.partial`：区分"完全没 output 可以重试"和"已生成一半要幂等处理"。
- `TurnDone.provider_state`：opaque，存什么由 adapter 决定（Responses API 的 `previous_response_id` 等）。
- `TurnDone.raw_stop_reason`：映射过的 stop_reason 不能丢掉原始值，诊断时要看。

#### 4.1.1 Anthropic thinking block 状态机规格（v3 新增）

**背景**：v2 的伪代码假设 `signature_delta` 是 `thinking_delta.provider_data` 的子字段。这是错的。Anthropic 真实的 SSE 协议中：

```
event: content_block_start    { "index": 0, "content_block": { "type": "thinking" }}
event: content_block_delta    { "index": 0, "delta": { "type": "thinking_delta", "thinking": "段..." }}
event: content_block_delta    { "index": 0, "delta": { "type": "thinking_delta", "thinking": "落..." }}
event: content_block_delta    { "index": 0, "delta": { "type": "signature_delta", "signature": "EucBCk..." }}
event: content_block_stop     { "index": 0 }
event: content_block_start    { "index": 1, "content_block": { "type": "text" }}
event: content_block_delta    { "index": 1, "delta": { "type": "text_delta", "text": "..." }}
...
```

**关键观察**：
1. `signature_delta` 是**独立的 content_block_delta 类型**，与 `thinking_delta` 同级
2. `signature` 一次性发送（非流式分片），但仍是 SSE event
3. `content_block_stop` 才是块边界
4. `redacted_thinking` 是 `content_block.type` 的一种，不是 delta 类型

**adapter 状态机要求**：

```python
class AnthropicThinkingBlockAccumulator:
    """每个 content block 一个实例，按 index 索引

    v6 修正：补 data 字段（v5 实现里有，规格漏写）。
    redacted_thinking 块的 data 是 content_block_start 一次性给的加密 blob。
    """
    block_index: int
    is_redacted: bool          # 由 content_block_start 决定
    text_chunks: list[str]     # thinking_delta 累积（仅普通 thinking 用）
    signature: str | None      # signature_delta 一次性写入（仅普通 thinking）
    data: str | None           # v6 新增：redacted block 的 data 字段（content_block_start 给）
    closed: bool               # content_block_stop 触发

    def feed(event):
        # content_block_start with type=thinking → 创建实例
        # content_block_start with type=redacted_thinking →
        #   创建实例 + is_redacted=True + data = event.content_block.data  (v6 修正)
        # content_block_delta type=thinking_delta → text_chunks.append
        # content_block_delta type=signature_delta → signature = event.signature
        # content_block_stop → closed = True，emit ReasoningBlockEnd

    def to_block() -> ReasoningBlock:
        return ReasoningBlock(
            text="".join(text_chunks),
            signature=signature,
            redacted=is_redacted,
            data=data,  # v6 修正：必须传 data，否则 redacted round-trip 失败
        )
```

**adapter yield 序列**（按 SSE 顺序）：

| Anthropic SSE 事件 | adapter yield |
|------|-------|
| content_block_start (type=thinking) | （内部建 accumulator，不 yield）|
| content_block_delta (thinking_delta) | `ReasoningDelta(text=delta.thinking, block_index=N)` |
| content_block_delta (signature_delta) | `ReasoningSignature(block_index=N, signature=delta.signature)` |
| content_block_stop | `ReasoningBlockEnd(block_index=N, redacted=accumulator.is_redacted)` |

**回传时（build_request）**：从 `StandardMessage.content` 里的 `ReasoningBlock` 重建（v5 修正）：

```python
def _serialize_reasoning_block(block: ReasoningBlock) -> dict:
    """v5 关键：redacted 用 data 字段，普通 thinking 用 thinking + signature。
    绝对不要把 redacted 写成 {"type":"redacted_thinking", "thinking":...}——
    Anthropic 会拒绝。"""
    if block.redacted:
        # data 是加密 blob，必须存在（accumulator 在 content_block_start 已写入）
        assert block.data is not None, "redacted ReasoningBlock 必须有 data 字段"
        return {
            "type": "redacted_thinking",
            "data": block.data,
        }
    else:
        result = {"type": "thinking", "thinking": block.text}
        if block.signature:
            result["signature"] = block.signature
        return result
```

**测试约束**（characterization test 必须覆盖）：
- thinking 块文本顺序保留
- signature 写入正确
- redacted 块完整 round-trip（不丢内容）
- 多 thinking 块（tool 前后各一段）通过 block_index 正确分组
- text 和 thinking 块在同一消息里交错时顺序正确

### 4.2 标准消息结构

```python
# agent_runner/model_adapter/messages.py

@dataclass(frozen=True)
class TextBlock:
    type: Literal["text"] = "text"
    text: str = ""
    provider_data: dict | None = None  # citations、annotations 挂这里

@dataclass(frozen=True)
class ReasoningBlock:
    """思维链块。Anthropic thinking 会有 signature + redacted，这里保留。

    **redacted 块的特殊处理**（v4 修正）：
    Anthropic 的 redacted_thinking 不是普通文本，是加密 blob，使用 `data` 字段
    （而非 `thinking` 字段）。回传时必须按原始格式：
    - 普通 thinking: `{"type": "thinking", "thinking": text, "signature": "..."}`
    - redacted: `{"type": "redacted_thinking", "data": "..."}`（无 thinking/signature）
    """
    type: Literal["reasoning"] = "reasoning"
    text: str = ""                                  # 普通 thinking 文本（redacted 时为空）
    signature: str | None = None                    # Anthropic 的 block 签名（普通 thinking 用）
    redacted: bool = False                          # 是否是 redacted thinking
    data: str | None = None                         # redacted 时的加密 blob（仅 redacted=True 时有值）
    provider_data: dict | None = None               # 其他 provider-specific 字段

@dataclass(frozen=True)
class ToolUseBlock:
    type: Literal["tool_use"] = "tool_use"
    id: str = ""
    name: str = ""
    input: dict = field(default_factory=dict)

@dataclass(frozen=True)
class ToolResultBlock:
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str = ""
    content: str | dict = ""
    is_error: bool = False
    provider_data: dict | None = None

@dataclass(frozen=True)
class ImageBlock:
    """用户输入的图片。阶段 1 非目标，阶段 2 启用"""
    type: Literal["image"] = "image"
    source: str  # base64 / url
    mime_type: str

@dataclass(frozen=True)
class CacheMarker:
    """prompt caching 标记（Anthropic cache_control / OpenAI 隐式）"""
    type: Literal["cache_marker"] = "cache_marker"
    ttl: Literal["ephemeral", "5m", "1h"] = "ephemeral"

StandardContentBlock = (TextBlock | ReasoningBlock | ToolUseBlock
                        | ToolResultBlock | ImageBlock | CacheMarker
                        | "InvalidToolCall")  # v5：invalid tool call 入 content 保留顺序

@dataclass(frozen=True)
class StandardToolCall:
    id: str
    name: str
    input: dict  # 已成功解析
    encoding: Literal["native_json", "xml_bare", "xml_json_wrapped"] = "native_json"
    # encoding 是终态真相：流解析完成后才能确定（XML bare vs json-wrapped 必须看到完整 payload）

@dataclass(frozen=True)
class InvalidToolCall:
    """tool args JSON 解析失败的落点"""
    id: str
    name: str
    raw_args: str          # 原始字符串
    parse_error: str
    index: int
    encoding: Literal["native_json", "xml_bare", "xml_json_wrapped"] | None = None
    # 解析失败时 encoding 可能也无法确定，允许 None

@dataclass(frozen=True)
class StandardTool:
    name: str
    description: str
    input_schema: dict  # JSON Schema
    provider_data: dict | None = None  # Anthropic cache_control 等

@dataclass(frozen=True)
class ProviderState:
    """opaque provider state。不同 provider 存不同东西。
    engine / DB 只把它当黑盒持久化+回传，adapter 负责读写。
    Responses API 存 previous_response_id；Anthropic 存什么可能以后扩"""
    kind: str  # 标识 provider 类型，如 "openai_responses"
    data: dict

@dataclass(frozen=True)
class StandardMessage:
    """v4 关键修正：content 是唯一主真相源。

    ReasoningBlock 直接放 content 数组里（保留与 text/tool_use 的交错顺序），
    不再有顶层 reasoning_blocks 字段。这样 build_request 和持久化都只读 content，
    避免双主真相源的不一致风险。
    """
    role: Literal["user", "assistant", "system"]
    content: list[StandardContentBlock]
    provider_state: ProviderState | None = None
    metadata: dict | None = None  # 扩展逃生口

    # 阶段 1 兼容辅助方法（不持久化，运行时派生）
    def reasoning_view(self) -> list[ReasoningBlock]:
        """convenience view：从 content 提取所有 ReasoningBlock"""
        return [b for b in self.content if isinstance(b, ReasoningBlock)]

    def text_view(self) -> str:
        """convenience view：拼接所有 text blocks"""
        return "".join(b.text for b in self.content if isinstance(b, TextBlock))
```

**设计要点**（Codex 反馈吸收）：
- **reasoning 不再是 str**，是 `list[ReasoningBlock]`。Anthropic signature / redacted 有位置存
- **InvalidToolCall** 是一等公民（现有 engine 已有 input_parse_error 处理，协议不应该假装没有）
- **ImageBlock / CacheMarker** 列出但标记阶段 1 非目标，避免后面往 metadata 塞逃生口
- **StandardTool** 有 provider_data，Anthropic cache_control 挂这里
- **ProviderState** 是 opaque 黑盒，engine 只负责持久化+回传，不解析

### 4.3 能力声明——下沉到 Profile

**Codex P0 反馈**：capabilities 不能挂 Adapter 类上。同一个 `OpenAICompatAdapter` 要服务 DeepSeek / Kimi / GLM / Claude via 网关，它们的 `thinking_must_roundtrip` / `supports_reasoning_stream` 不一样。

**解决**：

```python
# agent_runner/model_profile.py（扩展现有类型）

@dataclass(frozen=True)
class ThinkingExtractionConfig:
    """thinking 字段如何从 provider stream 提取的子配置（v3 改成 sub-schema）。

    模式说明：
    - "none"：模型没思维链
    - "openai_field"：从 delta.reasoning_content / delta.model_extra.reasoning_content 取
                      （DeepSeek thinking 模式、Kimi、GLM-Zero-Preview 等）
    - "xml_tag"：模型把思维链嵌在文本里，用配置的 open_tag/close_tag 包裹
                 （DeepSeek-R1-Lite、某些 Llama fine-tune）
    - "anthropic_block"：通过独立 SSE content_block (type=thinking) + signature_delta
                         传输（Claude 3.7+, Claude 4 系列）
    - "openai_responses"：OpenAI Responses API 的 reasoning summary
    """
    mode: Literal["none", "openai_field", "xml_tag", "anthropic_block", "openai_responses"] = "none"

    # 仅 mode="xml_tag" 时使用
    open_tag: str | None = None    # 如 "<think>"
    close_tag: str | None = None   # 如 "</think>"

    # 是否带 signature（Anthropic 系列 must_roundtrip 时为 True）
    has_signature: bool = False

    # 是否必须把上一轮的 reasoning_content 原样回传
    # v4 默认值修正为 False：mode="none" 模型不应该默认进入"必须回传"策略
    # DeepSeek thinking / Anthropic native 在各自 profile 显式设 True
    must_roundtrip: bool = False

    # 仅 Anthropic 系列：thinking budget（Claude extended thinking）
    budget_tokens: int | None = None


@dataclass(frozen=True)
class ModelCapabilities:
    """模型级能力声明，和 Adapter 类解耦"""
    # Thinking 子树（v3 改成 sub-schema）
    thinking: ThinkingExtractionConfig = field(default_factory=ThinkingExtractionConfig)

    # Tool use
    supports_tool_use: bool = True
    tool_call_style: Literal[
        "openai_native",     # OpenAI tools/tool_calls
        "anthropic_blocks",  # content blocks type=tool_use
        "gemini_functions",  # parts.functionCall
    ] = "openai_native"
    supports_parallel_tool_calls: bool = True
    max_tool_calls_per_turn: int = 64        # 业务策略，超了 adapter 拒绝
    max_parallel_tool_calls: int = 10

    # Context
    max_context: int = 128000
    max_output: int = 8192

    # Multimodal
    supports_vision: bool = True
    supports_audio: bool = False

    # Caching
    supports_prompt_caching: bool = False
    prompt_caching_style: Literal["none", "anthropic_marker", "openai_implicit"] = "none"

    # Streaming
    supports_stream_usage: bool = True
    supports_partial_retry: bool = False  # 见 §8 风险表 #7 + §10 Q10 的明确化

    # Grounding/Search
    supports_grounding: bool = False
    grounding_style: Literal["none", "gemini_search", "anthropic_citations"] = "none"


@dataclass(frozen=True)
class ProtocolLimits:
    """协议层资源硬护栏（v3 引入，v4 补全字段并明确执行层）。

    这些是**安全防 DoS 边界**，必须在 adapter/parser 边界生效，否则恶意/异常
    payload 已经进入 engine 状态机。和 ModelCapabilities 的"业务策略"分层。

    设计参考：selfagency/llm-stream-parser ProcessorOptions（但不照搬到大 options）
    """
    # === Transport 层执行（HTTP/SDK 边界，原始字节流）===
    max_total_stream_bytes: int = 16 * 1024 * 1024   # 整个 turn 累计原始流上限（16 MiB）
    # max_chunk_bytes 不在这里——原因见下文执行层说明

    # === Adapter/Parser 层执行（已 SDK 反序列化的对象）===
    max_tool_arg_bytes: int = 256 * 1024       # 单 tool args 累计字节（128 KiB selfagency → 256 KiB）
    max_tool_calls_per_turn_hard: int = 256    # 比 capabilities.max_tool_calls_per_turn 更宽的硬上限
    max_xml_nesting_depth: int = 64            # XML thinking tags / XML tool calls 解析时
    max_json_depth: int = 64                   # JSON 解析（含 tool args）
    max_json_keys: int = 4096                  # 单 JSON object 总 key 数上限（v4 补，selfagency 也有）

    # === 通用 ===
    max_warnings_per_turn: int = 100           # 防 warning 风暴
    # 超限策略（v5 统一）：raise transport/parser-level exception，**不进 StandardEvent**
    # 理由：ErrorEvent 仅承载 stream 内部的软错误 chunk，"adapter 不能伪造 ErrorEvent"
    # 是协议不变量。超限是基础设施问题，应以 exception 形式让 engine 决定重试/失败。
    # 实施：
    #   - transport 层：max_total_stream_bytes 超限 → ProtocolLimitExceededError
    #   - adapter/parser 层：max_tool_arg_bytes / max_json_depth / max_xml_nesting_depth
    #     超限 → ProtocolLimitExceededError（include adapter_kind/limit_name/observed_value）
    # engine 接住后：emit assistant_turn_ended(reason=protocol_limit, incomplete=True) +
    # 不重试（这通常是异常或恶意 payload，重试也会再撞）


@dataclass(frozen=True)
class ResolvedModelProfile:
    """扩展现有字段。

    v7 关键：这是对现 app/services/agent_runner/model_profile.py 的向后兼容扩展，
    不是替换。阶段 1A 期间 engine.py / claude_client.py 仍读取旧字段。
    """
    requested_model: str
    provider_model_name: str
    base_url: str
    api_key: str

    # === 现有运行字段：阶段 1A 必须保留 ===
    sdk_type: str = "openai_compat"
    max_output_tokens: int = 8192
    context_window: int = 128000
    supports_function_calling: bool = True
    supports_reasoning_stream: bool = False
    supports_stream_usage: bool = True
    request_timeout_s: int = 600
    first_chunk_timeout_s: int = 300
    total_timeout_s: int = 1800
    tool_call_style: str = "native"

    # Adapter 选择 —— 只决定"协议族怎么翻译"
    # 阶段 1A 可由 sdk_type 派生，不要求 DB schema 立即新增字段
    adapter_kind: Literal["openai_compat", "anthropic_native", "openai_responses", "gemini_native"] = "openai_compat"

    # 模型能力 —— 决定"这个模型的具体行为"（业务策略）
    # 阶段 1A 可为空；Phase 1B 由现 flat 字段派生
    capabilities: ModelCapabilities | None = None

    # 协议安全护栏（v3 新增，全局可覆盖但有合理默认）
    protocol_limits: ProtocolLimits = field(default_factory=ProtocolLimits)
```

**存储**：`model_channels.capabilities` 存 JSON，或者拆成独立列（字段少）。

---

## 5. ModelAdapter 接口

> ⚠️ **STALE 警告（2026-05-03，Phase B-1 ship 后）**：
>
> 本节定义的 `ModelAdapter` Protocol（`build_request(messages, tools, profile, system_prompt)`）
> **与实际 shipped 的 OpenAICompatAdapter / AnthropicNativeAdapter 签名不一致**。这两个具体类的
> `build_request` 因为 OpenAI Responses API（reasoning_effort 字符串档）和 Anthropic Messages API
> （thinking.budget_tokens 整数）协议本身不同，没有共通签名可以抽。
>
> **当前 rd-llm-adapter 1.0.0 公开 API**：只暴露 `Transport` + `StreamParserSession` 两个 Protocol，
> 不暴露 `Adapter` 抽象。依赖具体类（OpenAICompatAdapter / AnthropicNativeAdapter）+ `adapter_kind`
> 字符串识别。原因：现有调用方（codesphere-saas）已 isinstance 分支，没有迫切的 Protocol 痛点；
> Adapter 抽象设计要等 B-3 engine 抽出后基于 `TurnRequest` 中间态定义。
>
> 本节中的 `StreamParserSession` 接口与实际 shipped 一致，仍然权威。
>
> 本节中 `ModelAdapter` Protocol 应**作为历史设计参考**阅读，**不要按它实现新 adapter**。

### 5.1 核心接口（拆分后）

**Codex 反馈**：原 `call_stream()` 把 HTTP/SDK 调用和事件解析混在一起，测试难做。拆开。

```python
# agent_runner/model_adapter/base.py
from typing import Iterable, Iterator, Protocol

class StreamParserSession(Protocol):
    """单 turn 的 stateful parser session（v5 重新设计）。

    **关键约束**：每个 LLM turn 一个实例，整个 turn 共享同一个 session。
    内部维护跨 chunk 累积状态（tool args buffer、block_index → call_id 映射、
    text/reasoning accumulator 等）。

    生产消费方式：
        session = adapter.create_parser_session(profile)
        async for raw_chunk in transport.stream(...):
            for event in session.feed(raw_chunk):
                # 消费 event
                ...
        # 流结束后调 finalize 拿 TurnDone（如果 transport 没 yield 出 message_stop）
        for event in session.finalize():
            ...

    测试消费方式：
        session = adapter.create_parser_session(profile)
        events = list(itertools.chain.from_iterable(
            session.feed(chunk) for chunk in recorded_chunks
        )) + list(session.finalize())
    """

    def feed(self, raw_chunk: Any) -> Iterable[StandardEvent]:
        """喂一个 raw chunk，yield 0 或多个 StandardEvent。

        实施约束（v6 加强）：
        - 同一 session 实例必须按时序顺序消费一个 turn 的所有 chunks
        - feed() 内部维护跨 chunk 累积状态（tool_state / block_kinds / text_buffers 等）
        - **TurnDone yield 后**，session 进入 closed 状态，后续 feed 应该 raise（防误用）
        """
        ...

    def finalize(self) -> Iterable[StandardEvent]:
        """流正常结束（transport 已停）。yield 还没发出的事件（如 TurnDone 聚合）。

        若 stream 中已经 yield TurnDone（如 Anthropic 的 message_stop 触发），这里返回空。
        若 stream 没自然给 TurnDone（如 OpenAI compat 流式 finish_reason 才知道），
        这里聚合并 yield 一次 TurnDone。
        """
        ...

    def finalize_on_error(self) -> Iterable[StandardEvent]:
        """transport 异常路径下调用，用于优雅 emit 已累积的部分内容。

        约束：
        - 不强制 yield TurnDone（异常时可能数据不完整）
        - 可以 yield 部分 TextBlock / ReasoningBlock 信息，让 engine 知道哪些已成功
        - **不要在这里 emit lifecycle event**（assistant_turn_ended）——那是 engine 的责任
        """
        ...


class ModelAdapter(Protocol):
    """协议翻译器。
    - build_request：纯函数（无状态）
    - create_parser_session：工厂方法，返回 stateful session
    """

    adapter_kind: str

    def build_request(
        self,
        *,
        messages: list[StandardMessage],
        tools: list[StandardTool],
        system_prompt: str,
        profile: ResolvedModelProfile,
    ) -> dict:
        """StandardMessage → provider 请求体 JSON。**纯函数**。

        负责：
        - role + content blocks 翻译（保留交错顺序）
        - ReasoningBlock 回传：普通 thinking 输出 `{"type":"thinking","thinking":text,"signature":...}`
          redacted 输出 `{"type":"redacted_thinking","data":data}`（绝不写 thinking 字段）
        - provider_state 恢复（Responses API 的 previous_response_id）
        - tool 格式翻译
        - prompt caching markers
        """
        ...

    def create_parser_session(
        self,
        profile: ResolvedModelProfile,
    ) -> StreamParserSession:
        """工厂方法：创建一个 turn 级的 stateful parser session。
        每次新的 LLM 调用都要新建实例，不能复用（状态会污染）。
        """
        ...

    def serialize_tool_result(
        self,
        result: ToolResultBlock,
    ) -> StandardContentBlock:
        """tool_result 给下一轮请求时的格式（通常就是 ToolResultBlock 本身，
        但 Anthropic 可能要塞 cache_control 等）"""
        return result


class Transport(Protocol):
    """HTTP/SDK 调用层。和 Adapter 解耦，engine 用。"""

    async def stream(
        self,
        request_body: dict,
        profile: ResolvedModelProfile,
    ) -> AsyncIterator[Any]:  # 返回原始 chunks
        """发起流式请求，yield 原始 chunk（未翻译）。
        负责：HTTP 连接、超时、SDK 实例化、重试退避的底层部分。

        **错误语义**（v5 明确）：
        - HTTP 4xx/5xx/超时/连接失败/ProtocolLimits 超限 → raise exception
        - exception 由上层 engine/_call_llm_with_retries 捕获处理
        - **不**伪造 ErrorEvent；ErrorEvent 仅用于 stream 内部的软错误 chunk
        """
        ...


class OpenAICompatTransport(Transport):
    """用 openai SDK 的 AsyncClient，现在 claude_client 就这么干"""
    ...


class AnthropicNativeTransport(Transport):
    """用 anthropic SDK 的 AsyncAnthropic"""
    ...
```

**分层意义**（v5 修正）：
- `StreamParserSession` 是 **stateful**——同一 session 实例消费整个 turn 的所有 chunks，跨 chunk 状态由 session 内部维护
- `build_request` 是 **纯函数**（StandardMessage → dict）
- `create_parser_session` 是 **工厂方法**（每个 turn 新建一个 session）
- 测试时：用 list/iterable 整段喂，或单 chunk 循环喂，行为应该等价（这是 session 的不变量）
- 生产时：与 transport.stream 的 async iteration 对接

### 5.2 engine 主循环（v5 改用 stateful session）

```python
async def _call_llm(messages, tools, profile) -> TurnDone:
    adapter = resolve_adapter(profile.adapter_kind)
    transport = resolve_transport(profile.adapter_kind)
    request_body = adapter.build_request(
        messages=messages, tools=tools,
        system_prompt=system_prompt, profile=profile,
    )
    # v5 关键：每个 turn 一个 session，跨 chunk 状态由 session 维护
    session = adapter.create_parser_session(profile)
    turn_done = None
    try:
        async for raw_chunk in transport.stream(request_body, profile):
            for event in session.feed(raw_chunk):
                turn_done = _dispatch_event(event, on_event, turn_done)
        # transport 流结束后 finalize（如果 message_stop 已触发，finalize 返回空）
        for event in session.finalize():
            turn_done = _dispatch_event(event, on_event, turn_done)
    except TransportException as exc:
        # v6 修正：claude_client 层不发 lifecycle event（assistant_turn_ended）
        # 只 emit 已累积的部分内容（assistant_stream 级别），然后 raise。
        # engine 才拥有 turn_id/message_id，由 engine 层负责 lifecycle 闭合。
        for event in session.finalize_on_error():
            _dispatch_event(event, on_event, None)
        raise  # 上抛给 engine 层，engine 决定 emit assistant_turn_ended + retry
    return turn_done


def _dispatch_event(event, on_event, turn_done):
    """单事件分发（不修改外部状态机，session 已经管好状态）"""
    if isinstance(event, TextDelta):
        await on_event({"type": "text_delta", "text": event.text, ...})
    elif isinstance(event, ReasoningDelta):
        await on_event({"type": "reasoning_delta", ...})
    elif isinstance(event, ToolCallArgsDelta):
        await on_event({"type": "tool_use_delta", ...})
    elif isinstance(event, SourceAdded):
        await on_event({"type": "sources_added", ...})
            elif isinstance(event, ErrorEvent):
                # v4 修正：阶段 1 不消费 partial 做续传，统一闭合状态后让 engine 重发整轮
                # event.partial 仅作日志/打点用（监控重发率、识别"已生成多少 token 后失败"）
                _record_partial_telemetry(event)  # 不影响控制流
                if event.retryable:
                    raise RetryableError(...)     # engine 重发整轮
                else:
                    raise ClaudeClientError(...)
                # 阶段 2+ 才会出现 PartialRetryError 路径（基于 capabilities.supports_partial_retry）
            elif isinstance(event, TurnDone):
                turn_done = event
    return turn_done
```

### 5.3 Adapter 注册表

```python
# agent_runner/model_adapter/registry.py
ADAPTERS: dict[str, ModelAdapter] = {
    "openai_compat": OpenAICompatAdapter(),
    "anthropic_native": AnthropicNativeAdapter(),      # 阶段 2
    "openai_responses": OpenAIResponsesAdapter(),      # 阶段 2
    "gemini_native": GeminiNativeAdapter(),            # 阶段 3
}

TRANSPORTS: dict[str, Transport] = {
    "openai_compat": OpenAICompatTransport(),
    "anthropic_native": AnthropicNativeTransport(),
    "openai_responses": OpenAIResponsesTransport(),
    "gemini_native": GeminiNativeTransport(),
}
```

---

## 6. 持久化分层（新增，Codex P0）

**Codex 反馈**：v1 文档说"DB 只存 normalized chat metadata"覆盖不了现状——`ask_user` 恢复靠 `engine_state_json` 存完整 transcript（含 tool_use/tool_result），不是 `messages.metadata_json`。

**解决**：分两层持久化。

### 6.1 MessageView（用户可见消息）

```python
# messages 表（现有表）
# 职责：展示用，前端 /messages API 拉取
# 粒度：一条用户输入 → 1 条 user message；一次 assistant 完整回复 → 1 条 assistant message
# 只存可见 content；reasoning 摘要可选存 metadata_json
```

这一层**不追求无损**，只要 UI 能还原对话流即可。

### 6.2 ConversationState（完整对话状态）

```python
# sessions.engine_state_json 继续使用（现有字段），但改存 normalized 结构
# 职责：engine 恢复用，支持 ask_user 暂停、GPT-5 Responses previous_response_id、
#       未来可能的 checkpoint rollback

# 结构
{
    "version": 2,
    "messages": [
        {
            "role": "user",
            "content": [{"type": "text", "text": "..."}]
        },
        {
            "role": "assistant",
            "content": [
                {"type": "reasoning", "text": "...", "signature": "..."},
                {"type": "text", "text": "..."},
                {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
            ],
            "provider_state": {"kind": "openai_responses", "data": {"previous_response_id": "..."}}
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]
        }
    ]
}
```

**阶段 1 策略**：**不动 `engine_state_json` 现有存储**。adapter 层只负责 LLM 边界，不碰恢复真相源。等阶段 1 稳定后再迁 engine_state_json 到 v2 结构。

### 6.3 兼容策略

- **读**：双读（先读 normalized `reasoning_blocks`，fallback 读旧 `reasoning_content` 字符串）
- **写**：阶段 1 双写（新旧字段都写），阶段 2 观察期后停写旧字段

---

## 7. 迁移计划

### 阶段 1：重构地基（行为 0 变化）

**预计工期**：Phase 1A 1-2 个工作日；Phase 1B 2-3 个工作日。v7 将原阶段 1 拆开，避免"唯一切点"和"DB/profile 同时改"互相冲突。

#### Phase 1A：OpenAI compat shim（当前实施范围）

**目标**：把 `claude_client.py` 内部的 OpenAI-compatible 请求构造、流式解析、旧事件包装拆到 `agent_runner/model_adapter/`，但对 `engine.py` 保持 0 行为变化。

**允许改动**：
- `app/services/agent_runner/model_adapter/` 新增协议事件、消息块、OpenAI compat adapter/parser、transport
- `app/services/agent_runner/claude_client.py` 内部切到 shim
- `tests/test_model_adapter_openai_compat.py` 增加 characterization tests

**明确不改**：
- `engine.py`
- `project_service.py` / `executor.py` 持久化恢复
- `ResolvedModelProfile` schema/DB 字段
- `engine_state_json`
- 前端事件协议

#### Step 1.1：新建目录结构
```
app/services/agent_runner/model_adapter/
├── __init__.py
├── capabilities.py     # ModelCapabilities + ProtocolLimits
├── events.py           # StandardEvent 定义
├── messages.py         # StandardMessage + blocks
├── base.py             # StreamParserSession + Transport Protocol
├── openai_compat.py    # OpenAICompatAdapter
└── transports.py       # OpenAICompatTransport

app/services/agent_runner/reasoning_metadata.py
tests/test_model_adapter_openai_compat.py
tests/test_model_adapter_engine_golden.py
tests/test_reasoning_metadata.py
```

#### Step 1.2：写 characterization test（**先于代码**）

**3 层测试矩阵（Codex 建议具体化）**：

**L1：`_build_oai_messages` 输出对照**
- 至少 6 组样例：
  - 纯文本 assistant
  - assistant + reasoning_content
  - assistant 文本 + tool_use 混合
  - user tool_result
  - 多 text blocks 仅第一条挂 reasoning_content
  - supports_function_calling=False 时 tools 被清空
- 断言 `OpenAICompatAdapter.build_request()` 输出 JSON 与现 `_build_oai_messages()` **逐字段等价**

**L2：流式 chunk 解析对照**
- 至少 8 组 fake chunk 序列：
  - 纯 text delta
  - `model_extra.reasoning_content` 增量
  - text/reasoning 交错
  - 单个 tool call 参数分片
  - 两个并行 tool call 按 index 交错
  - 末尾 usage chunk
  - `finish_reason` 映射（stop / tool_calls / length / content_filter）
  - tool args JSON 解析失败（保留 `_parse_error` 语义）
- 断言 `OpenAICompatAdapter.parse_stream_chunks(chunks)` 产出的 `StandardEvent` 序列 + `TurnDone` 聚合字段 与现 `create_streaming_turn()` 返回 dict **等价**
- 额外加入 selfagency 风格 adversarial cases：空 choices、usage-only chunk、id/name/args 后到、malformed tool args 不抛到 engine

**L3：engine 黑盒 golden test（v8 已补主路径 / 异常 / length / length_limit / ask_user / 空响应重试 / max_turns / partial stream retry，灰度前建议继续扩展）**
- monkeypatch LLM 边界（用 fake adapter 返回预录 StandardEvent 序列）
- 对比改造前后 `on_event` 事件序列 + `AgentResult.messages` 完全一致
- 至少 7 条主路径：
  - 普通 text-only
  - tool_use → tool_result → 继续
  - length 自动续写 1 次
  - length 连续到上限
  - ask_user 暂停
  - loop break synthetic closing
  - 空响应重试
  - **partial stream 中断后重发整轮**（v3 新增，验证 engine 阶段 1 不做续传）

#### Step 1.2.5：StreamRecorder & Event Replay 工具（Phase 2）

**动机**：L2 测试如果只用人工编造的 fake chunks，会遗漏现实中真实出现的奇怪场景（DeepSeek 偶发的双 reasoning_content delta、Kimi 在 model_extra 里塞自定义字段等）。selfagency/llm-stream-parser 项目代码扎实但**没有这个工具**——v2 借鉴时误以为它有。v3 必须自己做。

**v10 落地状态**：Phase 2A 已实现离线录放工具；Phase 2B 已在 `claude_client.create_streaming_turn()` 成功路径接入 ENV-gated 采样入口。默认关闭，不改变 LLM 主链路行为。文件生命周期和 S3/内部存储同步仍留给后续运维集成。

**v4 实施前置（Codex 反馈）**：现 `claude_client.py` 的 raw chunk 解析和网络流消费**耦合**在 `create_streaming_turn` 内部。要让 StreamRecorder 能"同一份 raw_chunks 喂旧 parser 和新 adapter"做 diff，必须**先抽出 legacy parser 纯函数**：

```python
# claude_client.py 重构第一步（在 OpenAICompatAdapter 之前做）
def legacy_parse_openai_chunks(
    raw_chunks: Iterable[ChatCompletionChunk],
    model: str,
) -> tuple[dict, list[dict]]:
    """把 v3 之前的 raw chunk 解析逻辑抽成纯函数。

    返回：(legacy_dict, legacy_event_list)
      - legacy_dict: 现 create_streaming_turn 返回的旧 dict
      - legacy_event_list: 现 on_event 的全部事件序列

    没有 IO、没有 await、没有 SDK 调用。便于 fixture 喂入做 diff。
    """
    ...
```

完成这一步后 StreamRecorder 才能：
1. 录制时同时跑新 adapter 和 `legacy_parse_openai_chunks`，把 `expected_legacy_dict` 和 `expected_events` 落盘
2. 测试时从磁盘读 raw_chunks，分别喂新旧路径，diff 输出

**v9 实施修正**：Phase 1A 已经把旧 parser 收敛进 `OpenAICompatParserSession`，所以 Phase 2A 不再强行补 `legacy_parse_openai_chunks()` 纯函数。录制文件里的 `expected_events` / `expected_legacy_dict` 作为 legacy 行为锁，replay 时把同一份 `raw_chunks` 喂当前 adapter，再对比 legacy 输出。后续如果需要和更早 commit 做三方 diff，再从 git 历史提取 legacy parser。

**StreamRecorder 设计**：

```python
# agent_runner/model_adapter/recorder.py

@dataclass
class RecordedTurn:
    """录制的一个 LLM turn 的完整原始流"""
    turn_id: str
    timestamp: str
    profile_snapshot: dict        # ResolvedModelProfile 的 dict 形式（脱敏 api_key）
    request_body: dict            # adapter.build_request 出参
    raw_chunks: list[dict]        # provider 原始 chunks（已 JSON 化）
    expected_events: list[dict]   # 旧 claude_client 产出的事件序列（diff 基准）
    expected_legacy_dict: dict    # 旧 create_streaming_turn 返回值（行为锁）

class StreamRecorder:
    """阶段 1 录放工具。
    - 灰度期：拦截 saas-test 真实流量（按 sample rate / by user 抓样）
    - 测试期：磁盘上的样本喂新 adapter，对比输出
    - 故障归因：用户报"reasoning 丢了"，重放看是哪一层丢的
    """
    def record_turn(self, turn: RecordedTurn, output_dir: Path) -> None: ...
    def load_turn(self, path: Path) -> RecordedTurn: ...

    def replay_through_adapter(
        self, recorded: RecordedTurn, adapter: ModelAdapter,
    ) -> tuple[list[StandardEvent], TurnDone]:
        """喂 raw_chunks 给 adapter.parse_stream_chunks，返回 yield 序列"""
        ...

    def diff_against_legacy(
        self, recorded: RecordedTurn, new_events: list[StandardEvent],
    ) -> list[str]:
        """对比新事件序列和录制的 expected_events，返回差异列表"""
        ...
```

**录制 fixtures 计划**（阶段 1 第一周完成）：

| 来源 | 抓多少 | 覆盖什么 |
|------|-------|---------|
| saas-test 真实流量 | ≥50 个 turn | 普通 chat / tool_use / ask_user / length 续写 / loop break / 异常重试 |
| DeepSeek thinking 模式 | ≥20 | reasoning_content 各种边界 |
| Kimi | ≥10 | model_extra 字段 |
| Claude via 网关 | ≥10 | 网关转译的 tool_calls |
| GPT via 网关 | ≥10 | 网关转译的 reasoning |

**实现位置**：`app/services/agent_runner/model_adapter/recorder.py`

**v9 已实现 API**：
- `RecordedTurn.create(...)`：统一 JSON 化 raw chunks，并脱敏 profile secrets。
- `StreamRecorder.record_turn(...) -> Path`：写 `*.jsonl.gz`，单 turn 单文件。
- `StreamRecorder.load_turn(path) -> RecordedTurn`：支持 gzip/plain JSONL。
- `StreamRecorder.replay_through_adapter(recorded, adapter) -> tuple[ReplayEvents, TurnDone]`；`ReplayEvents.legacy_events` 保留 raw chunk 边界，避免跨 chunk 误合并 tool name/args delta。
- `StreamRecorder.diff_against_legacy(recorded, new_events) -> list[str]`。
- `legacy_events_from_standard_events(events)`：把标准事件还原成现有 legacy stream event 序列，供 diff 使用。

**v10 采样 ENV**：
- `MODEL_ADAPTER_RECORD_TURNS=1`：开启采样；默认关闭。
- `MODEL_ADAPTER_RECORD_DIR=/tmp/model_adapter_recordings`：输出目录。
- `MODEL_ADAPTER_RECORD_SAMPLE_RATE=0.1`：采样率，范围 `0..1`，默认 `1`。
- `MODEL_ADAPTER_RECORD_INCLUDE_MESSAGES=1`：允许保留 request messages 原文；默认不设置时 scrub request message content 和 tool arguments。

**v11 回放测试入口**：
- 默认目录：`tests/fixtures/recorded/model_adapter`
- 覆盖目录：`MODEL_ADAPTER_RECORDED_FIXTURES_DIR=/path/to/fixtures`
- 执行：`uv run pytest tests/test_model_adapter_recorded_fixtures.py`
- 无 fixtures 时 skip；有 fixtures 时逐个 `StreamRecorder.load_turn()` + `replay_through_adapter()` + `diff_against_legacy()`。

**用途**：
1. **L2 测试 fixtures**：直接用真实流量样本，不用手写 fake chunks
2. **回归测试**：每次 adapter 改动跑一遍所有录制样本
3. **故障归因**：线上 bug 复现时调出对应 turn 的 raw_chunks 重放
4. **阶段 1 灰度对比**：同一个 raw_chunks 喂新旧两个 adapter，diff 任何不一致

**脱敏要求**：
- `profile_snapshot` 里的 `api_key` 字段必须脱敏（仅留前缀）
- `request_body.messages` 里如有 PII 信息要按需 redact（生产敏感数据，不上 git）
- 录制文件存 `tests/fixtures/recorded/*.jsonl.gz`，**不进 git**，按需从 S3 / 内部存储拉

#### Step 1.3：shim 单切点（v7 锁定）

**唯一切点**：`claude_client.py` 内部的 `create_streaming_turn` 函数。

**engine.py 在 Phase 1A 完全不动控制流**——`_call_llm_with_retries` 只是重试包装层，调用 `create_streaming_turn` 拿旧 dict 返回值。所有上层逻辑（`assistant_message` 构造、`length` 续写、`ask_user` 合成、loop break）继续消费旧 dict。

```python
# claude_client.py（Phase 1A 唯一运行路径改动文件）

# 1. OpenAICompatAdapter 作为底层（在 model_adapter/ 模块）
class OpenAICompatAdapter:
    def build_request(...): ...
    def create_parser_session(profile) -> StreamParserSession: ...

class OpenAICompatParserSession:
    """stateful session，每个 turn 一个实例。维护跨 chunk 状态：
    - tool_calls_by_index: dict[int, {id, name, args_buffer, encoding}]
    - text_buffer / reasoning_buffer
    - usage / finish_reason
    """
    def feed(raw_chunk) -> Iterable[StandardEvent]: ...
    def finalize() -> Iterable[StandardEvent]: ...
    def finalize_on_error() -> Iterable[StandardEvent]: ...

# 2. create_streaming_turn 改成 shim（**签名严格不变**）
async def create_streaming_turn(
    *, system_prompt, messages, tools, model, api_key, max_tokens,
    profile, on_event, ...
) -> dict:
    """阶段 1 内部：构造 adapter + transport，跑流，最后包装成旧 dict 返回。
    所有外部行为（on_event 序列、返回 dict 字段）严格不变。
    """
    adapter = OpenAICompatAdapter()
    transport = OpenAICompatTransport()
    request_body = adapter.build_request(
        messages=messages,  # 阶段 1 直接吃 legacy dict，Phase 2 再切 StandardMessage
        tools=tools,
        system_prompt=system_prompt,
        profile=profile,
    )

    # v5 修正：用 stateful session 而非 per-chunk parse
    session = adapter.create_parser_session(profile)
    turn_done: TurnDone | None = None
    try:
        async for raw_chunk in transport.stream(request_body, profile):
            events = list(session.feed(raw_chunk))
            for legacy_event in _standard_events_to_legacy_deltas(events):
                await _emit_stream_event(on_event, legacy_event)
            for event in events:
                if isinstance(event, TurnDone):
                    turn_done = event
        # 流正常结束后 finalize（如果 stream 已 emit message_stop，finalize 返回空）
        events = list(session.finalize())
        for legacy_event in _standard_events_to_legacy_deltas(events):
            await _emit_stream_event(on_event, legacy_event)
        for event in events:
            if isinstance(event, TurnDone):
                turn_done = event
    except TransportException:
        # v6 关键：shim 不发顶层 lifecycle event。
        # 它没有 turn_id/message_id（那些是 engine 的），无权 emit assistant_turn_ended。
        # 这里只 emit 已累积事件（assistant_stream 级），让前端能看到失败前的部分内容；
        # 然后 raise，由 engine 层 catch 后做 lifecycle 收尾（见 §11.5 时序图）。
        # v7：finalize_on_error 不 yield TurnDone，不发终态 text/reasoning/tool_use。
        # 已发出的 delta 保留；最终 lifecycle 只由 engine 外层异常路径闭合。
        for legacy_event in _standard_events_to_legacy_deltas(session.finalize_on_error()):
            await _emit_stream_event(on_event, legacy_event)
        raise

    # 包装成 engine 仍在消费的旧 dict（字段名锁死，对应 engine 现读法）
    return {
        "stop_reason": _to_legacy_stop_reason(turn_done.stop_reason),  # tool_use→tool_calls
        "content": _turn_to_legacy_content(turn_done),
        "reasoning_text": "".join(b.text for b in turn_done.reasoning_blocks if not b.redacted),
        "text_content": "".join(b.text for b in turn_done.text_blocks),
        "usage": _to_legacy_usage(turn_done.usage),  # 没收到 usage chunk 时保持 {}
        "latency_ms": ...,
        "first_chunk_latency_ms": ...,
    }
```

**engine Phase 1A 唯一改动**：无。

#### Step 1.4：~~`_call_llm_with_retries` 边界切换~~（v4 删除）

**v3 此 step 是 v4 P0 修正点**——和 Step 1.3 描述了两个不同切点会导致实现分叉。v4 锁定**仅 Step 1.3 一个切点**，本 step 不做任何 engine 改动。

Phase 1A 行为锁验证：
- L3 golden test 跑 7 条主路径，对比改造前后 `on_event` 序列 + `AgentResult.messages` 完全一致
- 通过即说明 shim 模式行为 0 变化

#### Phase 1B：capabilities + DB 双读双写（已实施）

Phase 1A 稳定后实施以下内容；v8 已完成最小落地。

#### Step 1.5：Capabilities 派生

- `model_profile.py` 保留现有 flat 字段
- 新增 `adapter_kind/capabilities/protocol_limits` 时必须向后兼容
- `resolve_capabilities(profile_row, model_overrides)` 从现字段派生，不能替换 `ResolvedModelProfile` 旧字段
- DB schema 不动，capabilities 只在运行时 profile 内存对象上派生

#### Step 1.6：DB 字段双读双写

- `messages.metadata_json.reasoning_blocks`（新，标准结构 list[dict]）+ `reasoning_content`（旧，扁平字符串）都写
- 加载时优先读 new，fallback 读 old
- 不改 `messages.content`（仍是可见文本）
- 落点：`agent_runner/reasoning_metadata.py`，由 `executor.py` 和 `project_service.py` 复用
- 观察 1 周后决定停写旧字段

**engine_state_json 不碰**。

#### Step 1.7：删死代码 `app/services/workspace_support/llm/`

只保留 `model_config.py`（前端模型列表接口用）。

#### Step 1.8：测试+部署

- 全量 L1/L2/L3 测试
- saas-test 灰度，盯日志**至少 1 周**
- 对比指标：成功率、事件序列一致性、turn 结束原因分布、恢复成功率

**Phase 1A/1B 范围（v8 当前完成）**：
- ✅ 仅承诺 `OpenAICompatAdapter`（覆盖现有所有走网关的模型：DeepSeek / Kimi / GLM / Claude/GPT via 网关）
- ✅ L1/L2 characterization tests
- ✅ shim 模式接 `create_streaming_turn` 内部，`_call_llm_with_retries` 不动
- ✅ DB metadata 双读双写（不改 schema）：`reasoning_blocks` + legacy `reasoning_content`
- ✅ capabilities/profile 内存派生（不改 schema）：`adapter_kind/capabilities/protocol_limits`
- ❌ **不承诺**任何 native adapter（Anthropic / OpenAI Responses / Gemini）
- ❌ **不承诺** partial retry 续传（重发整轮）
- ❌ 不拆 engine.py
- ❌ 不动 engine_state_json
- ❌ 不改前端
- ❌ 不碰 length 续写 / ask_user / loop break 的内部逻辑

---

### 阶段 2：接入 Claude 原生 + GPT-5 Responses

**预计工期**：Claude 2-3 天，Responses 2-3 天

**前置条件**（v3 收紧）：阶段 1 saas-test 稳定运行 **1 周以上**，以下退出条件全部满足：
- `ask_user` 恢复率与基线一致
- `length` 续写事件序列与基线一致
- `tool parse error` 出现频次未异常上升
- 灰度组与基线组错误率差异 < 5%
- `rollback` 开关经过演练（一键切回旧路径）
- **Anthropic thinking 状态机 PoC** 已完成第一步（v12：独立 parser + fake SSE 单测）；仍需吃 100+ 个真实 Anthropic SSE chunk，验证 signature/redacted/多块场景全部 round-trip 无损。
- **replay/journal 工具**（StreamRecorder + diff_against_legacy）已能在生产环境抓 fixtures 并跑回归

#### Step 2.1: `AnthropicNativeAdapter`

> ⚠️ **v13 状态**：`AnthropicNativeAdapter.build_request()` 和 `AnthropicNativeParserSession` 的独立 PoC 已落地，但还没有接 registry / transport / engine。以下伪代码仍只作为 native adapter 完整接入的草图；真正上线前必须先用真实 request/SSE fixtures 验证。
>
> 阶段 1 不承诺 Anthropic 原生支持。这段代码的作用是：
> 1. 验证标准协议（StandardEvent / StandardMessage）能否承载 Anthropic native 语义
> 2. 给阶段 2 实施时一个起点
>
> **不要在阶段 1 实施时按这段写代码**——具体细节（如 `message_start` / `ping` / citations / SourceAdded 等事件）需要在 PoC 阶段对照真实 SSE 流补完。Codex review 已指出当前草图至少缺：
> - `message_start` 事件处理（input usage 在这里）
> - `ping` 事件（Anthropic 心跳）
> - `error` 事件（stream 内软错误）
> - `citations_delta` / `source` 事件（如启用 grounding）
>
> 阶段 2 启动时这段会重写，请以 PoC 实测结果为准。

关键差异：
- `content` 是 blocks 数组，`thinking` 是独立 block type
- `tool_use` 也是 content block，不是顶层 `tool_calls`
- 流式事件格式完全不同（`content_block_delta` / `content_block_stop` / `message_delta` / `message_stop`）
- `cache_control` marker 在 content block 上
- `thinking` block 有 `signature` 字段，**必须原样回传**（不要试图字符串化）

```python
class AnthropicNativeAdapter:
    adapter_kind = "anthropic_native"

    def build_request(self, messages, tools, system_prompt, profile):
        # system 单独字段
        system = [{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}]

        anthropic_messages = []
        for msg in messages:
            anthropic_blocks = []
            for block in msg.content:
                if isinstance(block, ReasoningBlock):
                    if block.redacted:
                        # v6 修正：redacted ReasoningBlock 必须有 data 字段（accumulator 不变量）
                        # silent skip 会让上层根本看不到不一致 → 改 raise 暴露问题
                        if block.data is None:
                            raise InvariantError(
                                "redacted ReasoningBlock without data field — "
                                "accumulator bug or DB corruption"
                            )
                        anthropic_blocks.append({
                            "type": "redacted_thinking",
                            "data": block.data,
                        })
                    else:
                        # 普通 thinking 必须带 signature 才能回传（Anthropic 强制要求）
                        anthropic_blocks.append({
                            "type": "thinking",
                            "thinking": block.text,
                            **({"signature": block.signature} if block.signature else {}),
                        })
                elif isinstance(block, TextBlock):
                    anthropic_blocks.append({"type": "text", "text": block.text})
                elif isinstance(block, ToolUseBlock):
                    anthropic_blocks.append({
                        "type": "tool_use", "id": block.id, "name": block.name, "input": block.input
                    })
                elif isinstance(block, ToolResultBlock):
                    anthropic_blocks.append({
                        "type": "tool_result", "tool_use_id": block.tool_use_id,
                        "content": block.content, **({"is_error": True} if block.is_error else {}),
                    })
            anthropic_messages.append({"role": msg.role, "content": anthropic_blocks})

        body = {
            "model": profile.provider_model_name,
            "system": system,
            "messages": anthropic_messages,
            "tools": [self._tool_schema(t) for t in tools],
            "max_tokens": profile.max_output_tokens,
        }
        if profile.capabilities.thinking.mode == "anthropic_block" and profile.capabilities.thinking.budget_tokens:
            body["thinking"] = {
                "type": "enabled",
                "budget_tokens": profile.capabilities.thinking.budget_tokens,
            }
        return body

    def create_parser_session(self, profile):
        return AnthropicNativeParserSession(profile)


class AnthropicNativeParserSession:
    """v5：stateful session，整个 turn 共享。维护跨 chunk 累积状态。"""

    def __init__(self, profile):
        self.profile = profile
        # 跨 chunk 状态
        self.block_kinds: dict[int, str] = {}    # idx -> "thinking" / "redacted_thinking" / "text" / "tool_use"
        self.tool_state: dict[int, dict] = {}    # idx -> {call_id, name, args_buf, encoding}
        self.redacted_data: dict[int, str] = {}  # idx -> data（redacted_thinking 用）
        # 顺序保留 content blocks，最后构造 TurnDone.content
        self.completed_blocks: list[StandardContentBlock | InvalidToolCall] = []
        # 当前累积的临时块
        self.text_buffers: dict[int, str] = {}        # idx -> 累积 text
        self.reasoning_state: dict[int, dict] = {}    # idx -> {text, signature, redacted, data}
        self.usage: UsageUpdate | None = None
        self.raw_stop_reason: str | None = None
        self.turn_done_emitted = False

    def feed(self, chunk) -> Iterable[StandardEvent]:
        etype = chunk.get("type")
        if etype == "content_block_start":
            yield from self._on_block_start(chunk)
        elif etype == "content_block_delta":
            yield from self._on_block_delta(chunk)
        elif etype == "content_block_stop":
            yield from self._on_block_stop(chunk)
        elif etype == "message_delta":
            # message_delta 通常带 stop_reason 和 usage 累加
            self.raw_stop_reason = chunk.get("delta", {}).get("stop_reason") or self.raw_stop_reason
            if "usage" in chunk:
                self.usage = _merge_usage(self.usage, chunk["usage"])
        elif etype == "message_stop":
            self.turn_done_emitted = True
            yield self._build_turn_done()

    def _on_block_start(self, chunk) -> Iterable[StandardEvent]:
        idx = chunk["index"]
        cb = chunk["content_block"]
        cb_type = cb["type"]
        self.block_kinds[idx] = cb_type
        if cb_type == "thinking":
            self.reasoning_state[idx] = {"text": "", "signature": None, "redacted": False, "data": None}
        elif cb_type == "redacted_thinking":
            # v5 关键：redacted block 的 data 在 content_block_start 就一次给完
            self.reasoning_state[idx] = {
                "text": "",
                "signature": None,
                "redacted": True,
                "data": cb.get("data"),  # 原始加密 blob，不能丢
            }
        elif cb_type == "text":
            self.text_buffers[idx] = ""
        elif cb_type == "tool_use":
            self.tool_state[idx] = {
                "call_id": cb["id"],
                "name": cb["name"],
                "args_buf": "",
                "encoding": "native_json",
            }
            yield ToolCallStart(call_id=cb["id"], index=idx, name=cb["name"], encoding_hint="native_json")

    def _on_block_delta(self, chunk) -> Iterable[StandardEvent]:
        idx = chunk["index"]
        kind = self.block_kinds.get(idx)
        d = chunk["delta"]
        dtype = d.get("type")
        if kind == "thinking" and dtype == "thinking_delta":
            self.reasoning_state[idx]["text"] += d["thinking"]
            yield ReasoningDelta(text=d["thinking"], block_index=idx)
        elif kind == "thinking" and dtype == "signature_delta":
            self.reasoning_state[idx]["signature"] = d["signature"]
            yield ReasoningSignature(block_index=idx, signature=d["signature"])
        elif kind == "redacted_thinking":
            # redacted 通常没有 delta，data 已在 start 拿到。future-proof：忽略未知 delta
            pass
        elif kind == "text" and dtype == "text_delta":
            self.text_buffers[idx] += d["text"]
            yield TextDelta(text=d["text"], block_index=idx)
        elif kind == "tool_use" and dtype == "input_json_delta":
            state = self.tool_state[idx]
            state["args_buf"] += d["partial_json"]
            # v6 修正：必填 index，call_id 可选（虽然 Anthropic 在 start 已给 id，
            # 但协议统一为 index 主键，便于和 OpenAI compat 共享 consumer 逻辑）
            yield ToolCallArgsDelta(
                index=idx,
                delta=d["partial_json"],
                call_id=state["call_id"],
            )

    def _on_block_stop(self, chunk) -> Iterable[StandardEvent]:
        idx = chunk["index"]
        kind = self.block_kinds.get(idx)
        if kind in ("thinking", "redacted_thinking"):
            rs = self.reasoning_state[idx]
            block = ReasoningBlock(
                text=rs["text"],
                signature=rs["signature"],
                redacted=rs["redacted"],
                data=rs["data"],  # v5 关键：data 字段贯穿到 ReasoningBlock
            )
            self.completed_blocks.append(block)
            yield ReasoningBlockEnd(block_index=idx, redacted=rs["redacted"])
        elif kind == "text":
            text = self.text_buffers[idx]
            self.completed_blocks.append(TextBlock(text=text))
        elif kind == "tool_use":
            state = self.tool_state[idx]
            raw_args = state["args_buf"]
            try:
                parsed = json.loads(raw_args) if raw_args else {}
                parse_error = None
            except json.JSONDecodeError as e:
                parsed = None
                parse_error = str(e)
            if parsed is not None:
                self.completed_blocks.append(ToolUseBlock(
                    id=state["call_id"], name=state["name"], input=parsed,
                ))
            else:
                # v5 关键：InvalidToolCall 也进 content（保留顺序）
                self.completed_blocks.append(InvalidToolCall(
                    id=state["call_id"], name=state["name"],
                    raw_args=raw_args, parse_error=parse_error,
                    index=idx, encoding="native_json",
                ))
            yield ToolCallEnd(
                call_id=state["call_id"], name=state["name"], index=idx,
                encoding="native_json", raw_args=raw_args,
                parsed_input=parsed, parse_error=parse_error,
            )

    def _build_turn_done(self) -> TurnDone:
        return _build_turn_done_from_blocks(
            self.completed_blocks,
            stop_reason_raw=self.raw_stop_reason or "stop",
            usage=self.usage,
        )

    def finalize(self) -> Iterable[StandardEvent]:
        """流正常结束。如果 message_stop 已 emit TurnDone，这里返回空"""
        if not self.turn_done_emitted:
            yield self._build_turn_done()
            self.turn_done_emitted = True

    def finalize_on_error(self) -> Iterable[StandardEvent]:
        """transport 异常时调用。

        异常路径不 yield TurnDone，也不补发终态 text/reasoning/tool_use。
        已经在 feed() 发出的 delta 保留；engine 外层负责 assistant_turn_ended(reason=error)。
        """
        return iter(())
```

#### Step 2.2: `OpenAIResponsesAdapter`

关键差异：
- `input` 参数替代 `messages`
- `previous_response_id` 做 session 连续（必须用 `ProviderState` 持久化）
- 响应事件是 `response.created` / `response.output_item.added` 等

#### Step 2.3: DB 配置

```sql
INSERT INTO model_channels (name, base_url, api_key, adapter_kind, capabilities, ...)
VALUES (
    'anthropic_native',
    'https://api.anthropic.com',
    'sk-ant-...',
    'anthropic_native',
    '{"thinking": {"mode": "anthropic_block", "has_signature": true, "must_roundtrip": true, "budget_tokens": 10000}, "tool_call_style": "anthropic_blocks", "supports_prompt_caching": true, "prompt_caching_style": "anthropic_marker"}'::jsonb,
    ...
);
```

#### Step 2.4: 灰度

- 先内部账号
- 对比指标：首字延迟、prompt caching 命中率、总成本、thinking 质量（抽样主观评价）

---

### 阶段 3：Gemini 原生 + 其他

**预计工期**：Gemini 3-4 天

按需接入。

---

## 8. 风险点 & 应对（v2 补齐）

| # | 风险 | 影响 | 应对 |
|---|------|------|------|
| 1 | 阶段 1 shim 模式下事件序列微小偏差 | 恢复链路、UI 状态机行为异常 | L3 golden test 全路径覆盖；灰度期对比事件序列 |
| 2 | Adapter 抽象过度导致复杂度失控 | 未来新 adapter 难写 | 只按当前真实需要抽象，第 4 个模型前不加新维度 |
| 3 | DB 字段名双轨期历史数据不一致 | 老会话丢 reasoning | 双读 fallback，观察 1 周后才停写旧字段 |
| 4 | Anthropic 原生工具调用格式和现 engine 不兼容 | 阶段 2 不敢上线 | Adapter 内完成 block ↔ StandardToolCall 双向翻译 |
| 5 | 直连 provider 的 rate limit | 用户 429 | 保留网关 fallback；Adapter 层做 key 池化和重试 |
| 6 | 多 adapter 并存期间 bug 归因困难 | 排查慢 | 日志统一带 `adapter_kind=xxx`；error trace 带 adapter name |
| **7** | **partial_output 重试导致重复输出** | 用户看到"重复说一遍"，DB token 重复计费 | **阶段 1**：保持现行为（重发整轮，可能重复，与 §10 Q10 一致）；adapter 层不做续传，但**必须正确 emit ErrorEvent.partial=True/False** 让 engine 有判断依据。**阶段 2+**：基于 `capabilities.supports_partial_retry` + provider-native 幂等机制实现真续传——但仅对 OpenAI Responses（`idempotency_key` header）有效；Anthropic 至本文撰写时无原生续传 API，只能业务层自做幂等或重发；DeepSeek/Kimi 等 OpenAI compat 不支持续传，永远走重发。**关键约束**：阶段 1 文档不承诺续传，避免在 engine 里写假实现。 |
| **8** | **lease mid-turn 过期** | 并发冲突，数据损坏 | 当前代码只在 turn 边界检查 lease（engine.py:306）；阶段 1 保持现状，但需监控 lease 异常率；阶段 2 考虑 turn 内续约 |
| **9** | **tool args JSON 解析失败** | 现代码已有 input_parse_error 处理但散落 | 协议里 `ToolCallEnd.parse_error` + `InvalidToolCall` 作为一等公民；engine 统一处理 |
| **10** | **delta/终态事件顺序约束** | 消费方状态机错乱 | 协议定义：TurnDone 必须是最后一个事件；ToolCallEnd 必须在该 call 所有 ArgsDelta 之后；适配器自检 |
| **11** | **Anthropic thinking signature 丢失** | 下一轮请求被拒（类似 DeepSeek reasoning_content 400） | ReasoningBlock.signature 必须带；阶段 2 入 Anthropic 原生前单独验证 |
| **12** | **Responses API previous_response_id 丢失** | 会话连续性断裂 | ProviderState 持久化；engine_state_json 阶段 1 不动，确保兼容 |
| **13** | **stream 中断后状态不一致** | 卡在 streaming 无法恢复 | **阶段 1**：ErrorEvent 闭合状态（emit TurnDone 收尾），engine 重发整轮，partial 仅打点；前端状态机靠 turn_ended 闭合卡片。**阶段 2+**：才考虑 provider-native 续传机制。 |

---

## 9. 工作量估算（v2 修正）

| 阶段 | 内容 | v1 估计 | v2 估计 | 变化原因 |
|------|------|---------|---------|---------|
| 阶段 1 | 地基+OpenAICompat+L1/L2/L3 test+shim+DB 双读双写 | 2-3 人日 | **3-5 人日** | Codex 指出 engine 改动被低估 |
| 阶段 1 灰度观察 | - | - | **5-7 天** | 新增，Codex 建议必须停 |
| 阶段 2 Anthropic | AnthropicNativeAdapter + 灰度 | 2-3 人日 | **3-5 人日** | 补 thinking signature 处理 |
| 阶段 2 Responses | OpenAIResponsesAdapter | 2-3 人日 | 2-3 人日 | - |
| 阶段 3 Gemini | GeminiNativeAdapter | 3-4 人日 | 3-4 人日 | - |
| 持续 | 新模型快速接入（复用 OpenAICompatAdapter） | < 1 人日/模型 | < 1 人日/模型 | - |

**总计**：主流模型全接完 14-18 个工作日 + 多轮灰度观察期。

---

## 10. 评审问题清单（v2）

**v1 6 问 + v2 新增 4 问（Codex 指出真正关键的问题）**。

### v1 原 6 问（更新建议）

**Q1：阶段 2 是否真的直连 Anthropic？**
- **立场**：**有条件直连**。前置条件：阶段 1 的 ReasoningBlock + signature 支持通过 L1/L2 test 验证。
- 理由：网关 429 是真问题；但协议没修好就直连，signature 丢失会把 prompt caching 收益抵消甚至倒扣。

**Q2：标准事件协议和前端 SSE 要不要合并？**
- **立场**：**明确分层**，tool_builder 继续做 StandardEvent → SSE 翻译。
- 理由：两者生命周期不同。Python 层 StandardEvent 要比 SSE 丰富（带 Source/ErrorEvent/provider_state），不能倒挂。

**Q3：DB schema 改不改？**
- **立场**：**阶段 1 不改 schema**，只在 `metadata_json` 加 `reasoning_blocks` key；阶段 2 评估是否加独立列。
- 理由：`engine_state_json` 是完整状态真相源，不是 metadata_json。要改的是**数据结构约定**，不是列结构。

**Q4：sdk_type 改名？**
- **立场**：保留 `sdk_type` 列但加 `adapter_kind` 字段；能力声明（capabilities）存单独 JSON 列或字段集合。
- 理由：Codex 指出直接改会绑死"协议族"和"模型特性"，两者是独立维度。

**Q5：阶段间停一停？**
- **立场**：**必须停**。阶段 1 → 阶段 2 之间至少 1 周灰度，退出条件具体化（见第 7 节阶段 2 前置条件）。

**Q6：前端改不改？**
- **立场**：**阶段 1 不改**，阶段 2+ 视能力演进决定（Gemini sources 展示、Anthropic citations 展示时需要）。

### v2 新增关键 4 问（Codex 指出 v1 缺失的）

**Q7：StandardMessage 协议是否无损？**
- **关键度**：🔴 最高。这决定未来接原生 provider 能否完整发挥能力。
- **具体**：
  - ReasoningBlock.signature 能否承载 Anthropic thinking signature？
  - provider_state 能否承载 Responses previous_response_id？
  - ProviderMetadata / Source / InvalidToolCall 协议成员是否完备？
- **建议**：阶段 1 完成后立即用 Anthropic thinking 小 PoC 验证无损性，再开阶段 2。

**Q8：`provider_state` 放哪？**
- **关键度**：🟡 高。
- **具体**：
  - `engine_state_json.messages[].provider_state` 内联存？还是独立表？
  - 跨 session 复用（previous_response_id）的 TTL 怎么定？
  - 多 provider 混用（同一会话前 10 轮 Claude、后 10 轮 GPT）怎么处理 provider_state 切换？
- **建议**：阶段 1 不动，阶段 2 启动前单独立项。

**Q9：capabilities 归属层级定死**
- **关键度**：🟡 高。
- **具体**：
  - 能力声明放 `ResolvedModelProfile` 还是单独 `ModelCapabilities` 表？
  - `model_channels.capabilities` 是 JSON 还是拆列？
  - 同渠道下不同模型（如渠道绑定"Claude 全系"）能力差异怎么表达？
- **建议**：阶段 1 先用 JSON 字段，阶段 2 若字段激增再评估拆列。

**Q10：partial stream 语义**（v3 与风险表 #7 对齐）
- **关键度**：🟡 高。
- **具体**：
  - `ErrorEvent.partial=True` 时 engine 是重发整轮还是"从上次中断处续传"？
  - 已 emit 给前端的 TextDelta 怎么幂等处理？
  - `tool_calls` 已 yield 部分后中断，后续 retry 是否会生成重复 tool_call_id？
- **决议（v3 锁定）**：
  - **阶段 1**：重发整轮，可能重复。adapter 必须正确 emit `ErrorEvent.partial=True/False`，但 engine 阶段 1 **不消费这个标志做续传**。前端可能短暂看到"AI 重复说一遍"，业务上可接受（出现频率 < 0.5%，且通常用户无感知）。
  - **阶段 2**：基于 `capabilities.supports_partial_retry` + provider-native 幂等机制实现真续传。OpenAI Responses 用 `idempotency_key` header；Anthropic 至本文撰写时无原生续传 API（不要假设有），需要业务层做幂等或退化到重发；DeepSeek/Kimi 等 OpenAI compat 不支持续传，永远走重发。
  - **关键约束**：阶段 1 文档**绝不承诺续传**。避免有人按"似乎应该续传"在 engine 里写假实现，引入隐 bug。
- **测试要求**：阶段 1 characterization test 必须包含"中途断流后重发"场景，确认前端事件序列虽有重复但状态机能正确闭合（不卡住）。

---

## 11. Capabilities 迁移规则（v4 新增）

**问题**：v3 设计的 `ModelCapabilities` + `ProtocolLimits` 是新结构，但现 `model_channels` 表是 flat 字段（`sdk_type` / `supports_reasoning_stream` / `tool_call_style` 等）。阶段 1 不能立刻改 schema，需要兼容函数从现有字段构造新 capabilities。

**迁移函数**：

```python
# agent_runner/model_profile.py

def resolve_capabilities(
    profile_row: ResolvedModelProfile,  # 现 model_profile.py 解析后的 dataclass
    model_overrides: dict | None,        # channel.models[model_name] 子配置
) -> ModelCapabilities:
    """从现 ResolvedModelProfile（flat 字段）构造新 ModelCapabilities。

    v6 关键：字段名严格对齐 model_profile.py:24-33 的真实定义：
        sdk_type: str = "openai_compat"
        supports_function_calling: bool = True   # 不是 supports_tool_use
        supports_reasoning_stream: bool = False
        supports_stream_usage: bool = True
        tool_call_style: str = "native"          # 不是 "openai_native"
        max_output_tokens: int = 8192
        context_window: int = 128000

    阶段 1 兼容期：现 schema 不变，capabilities 在内存里派生。
    阶段 2+ 评估是否往 channel 表加 capabilities JSON 列。
    """
    overrides = model_overrides or {}

    # Thinking 配置推断
    thinking = ThinkingExtractionConfig(mode="none", must_roundtrip=False)
    # supports_reasoning_stream 是真实字段（model_profile.py:28）
    if overrides.get("supports_thinking") or profile_row.supports_reasoning_stream:
        if profile_row.sdk_type in ("openai_compat", "openai_completions"):
            thinking = ThinkingExtractionConfig(
                mode="openai_field",
                must_roundtrip=overrides.get("thinking_must_roundtrip", True),
                has_signature=False,
            )
    # XML tag 模式（DeepSeek-R1 早期）
    if overrides.get("inline_thinking_tag_pair"):
        open_tag, close_tag = overrides["inline_thinking_tag_pair"]
        thinking = ThinkingExtractionConfig(
            mode="xml_tag",
            open_tag=open_tag,
            close_tag=close_tag,
            must_roundtrip=False,
        )

    # Tool call style 真实字段是 tool_call_style，默认值 "native"（不是 "openai_native"）
    raw_style = overrides.get("tool_call_style", profile_row.tool_call_style)
    # 标准化映射：真实代码 "native" → 标准协议 "openai_native"
    style_map = {
        "native": "openai_native",
        "openai_native": "openai_native",
        "anthropic_blocks": "anthropic_blocks",
        "gemini_functions": "gemini_functions",
    }
    tool_call_style = style_map.get(raw_style, "openai_native")

    return ModelCapabilities(
        thinking=thinking,
        tool_call_style=tool_call_style,
        # 真实字段是 supports_function_calling（model_profile.py:27），不是 supports_tool_use
        supports_tool_use=profile_row.supports_function_calling,
        max_context=profile_row.context_window,
        max_output=profile_row.max_output_tokens,
        supports_vision=overrides.get("supports_vision", False),
        supports_prompt_caching=False,  # 阶段 1 OpenAI compat 默认无
        supports_stream_usage=profile_row.supports_stream_usage,
        supports_partial_retry=False,   # 阶段 1 一律 False
        supports_grounding=False,
    )


def resolve_adapter_kind(profile_row: ResolvedModelProfile) -> str:
    """从 sdk_type 映射到 adapter_kind。

    真实 sdk_type 取值（来自 model_profile.py 默认值 + 历史用法）：
    - "openai_compat" / "openai_completions" → adapter "openai_compat"
    - "openai_responses" → "openai_responses"
    - "anthropic" / "anthropic_native" → "anthropic_native"
    - "gemini" / "gemini_native" → "gemini_native"
    """
    mapping = {
        "openai_completions": "openai_compat",
        "openai_compat": "openai_compat",
        "openai_responses": "openai_responses",
        "anthropic_native": "anthropic_native",
        "anthropic": "anthropic_native",
        "gemini_native": "gemini_native",
        "gemini": "gemini_native",
    }
    return mapping.get(profile_row.sdk_type, "openai_compat")
```

**阶段 1 落点**：
- `model_profile.py` 现有 `resolve_model_profile` 函数末尾调用 `resolve_capabilities` 填充 profile.capabilities
- DB schema 不动
- 阶段 2 评估是否加 `model_channels.capabilities_json` 列做显式存储

**测试覆盖**：
- 现 saas-test DB 里的所有 channel × model 组合都跑一遍 `resolve_capabilities`
- 断言关键字段（thinking.mode / thinking.must_roundtrip / tool_call_style）在迁移前后行为等价
- 加到 L2 characterization test 的初始化部分

---

## 11.5 异常路径时序图（v6 新增）

**目的**：明确 transport exception 时，shim / engine / 前端各层的责任划分。避免 v5 把 lifecycle event 错放在 shim 层导致重复闭合。

### 11.5.1 成功路径（基线）

```
engine                      claude_client (shim)         transport / adapter
  │                              │                              │
  │ create_streaming_turn(...)   │                              │
  ├─────────────────────────────>│                              │
  │                              │ session = adapter.create_*() │
  │                              │ async for chunk:             │
  │                              │   for event in session.feed(*)│
  │                              │     emit on_stream_event(*)  │
  │ <wrap as assistant_stream>   │ <─────                       │
  │                              │ session.finalize() done       │
  │                              │ return legacy_dict            │
  │ <─────────────────────────────│                              │
  │ 处理 response                                                 │
  │ if stop_reason="stop":                                        │
  │   emit assistant_turn_ended(reason="stop", incomplete=False)  │
  │ if stop_reason="tool_use":                                    │
  │   ... tool 调度                                                │
```

### 11.5.2 异常路径（v6 关键）

```
engine                      claude_client (shim)         transport / adapter
  │                              │                              │
  │ create_streaming_turn(...)   │                              │
  ├─────────────────────────────>│                              │
  │                              │ async for chunk:             │
  │                              │   ✅ 正常 emit 几条 delta     │
  │                              │   ✅ 网络异常 / 429 / 5xx     │
  │                              │   raises TransportException  │
  │                              │                              │
  │                              │ except TransportException:   │
  │                              │   for evt in session         │
  │                              │     .finalize_on_error():    │
  │                              │     emit on_stream_event(*)  │
  │                              │   raise                       │
  │ <─ TransportException ───────│                              │
  │                                                              │
  │ # _call_llm_with_retries 层                                   │
  │ if retryable and attempts_left:                              │
  │   ⚠️ 重试整轮 (新调 create_streaming_turn)                    │
  │   ↓                                                          │
  │   重新发送请求体（messages / tools 不变）                       │
  │   前端会看到「重复 delta」——v6 决议：可接受                     │
  │                                                              │
  │ # 重试用尽或不可重试                                            │
  │ except outer:                                                │
  │   emit assistant_turn_ended(                                 │
  │     turn_id, message_id,                                     │
  │     reason="error", incomplete=True                          │
  │   )                                                          │
  │   raise → tool_builder 转 SSE → 前端 V2 状态机闭合卡片         │
```

**关键不变量**：
1. `assistant_turn_ended` 只能由 engine 层 emit，**永远**不在 claude_client 层
2. 重试期间不发 `assistant_turn_ended`，只在最终成功或最终失败时发
3. session 层只负责 stream 内容的优雅 emit，不碰 lifecycle
4. transport 层只负责抛 exception，不碰 lifecycle

**对应 engine.py 改动**（阶段 1 实施时）：
- `_call_llm_with_retries` 不需要新增 catch（现有的就是这套语义）
- 真正改动是 `create_streaming_turn` shim 内部，去掉 v5 误加的 `await on_event(assistant_turn_ended)` 调用

### 11.5.3 ProtocolLimits 超限路径（区别于普通 transport exception）

```
adapter / parser            engine
  │                              │
  │ session.feed(chunk):         │
  │   args_buf += delta          │
  │   if len(args_buf) > limits  │
  │     .max_tool_arg_bytes:     │
  │     raise ProtocolLimit-     │
  │       ExceededError(...)     │
  │ ───────────────────────────> │
  │                              │ except ProtocolLimit-       │
  │                              │   ExceededError:            │
  │                              │   emit assistant_turn_ended(│
  │                              │     reason="protocol_limit",│
  │                              │     incomplete=True)         │
  │                              │   ❌ 不重试（异常 payload     │
  │                              │      重试也会再撞）           │
```

**与 TransportException 区别**：
- `TransportException` (429 / 5xx / timeout) → 可重试整轮，最终失败才闭合 with reason="error"
- `ProtocolLimitExceededError` → **不重试**，直接闭合 with reason="protocol_limit"

---

## 11.6 OpenAI compat → legacy event 映射表（v6 新增）

**目的**：阶段 1 shim 模式下，`OpenAICompatParserSession` yield 的 `StandardEvent` 必须能等价翻译回现有 `on_stream_event` 旧事件格式。这是 L2 characterization test 的对齐基准。

### 11.6.1 现有 legacy 事件清单

来源：`claude_client.py:240-300` 实际发出的所有 `_emit_stream_event` 调用：

| 旧事件 type | 字段 | 触发时机 |
|------------|------|---------|
| `text_delta` | `text` | `delta.content` 非空 |
| `reasoning_delta` | `text` | `delta.model_extra["reasoning_content"]` 非空 |
| `tool_use_delta` | `tool_use_id`, `index`, `name_delta`, `arguments_delta` | `delta.tool_calls[*]` 任何子字段更新 |
| `text` | `text` | 流结束聚合（Phase 1A shim 按旧路径继续 emit） |
| `reasoning` | `text` | 同上 |
| `tool_use` | `id`, `name`, `input` | 同上 |

### 11.6.2 StandardEvent → legacy event 映射

| StandardEvent | legacy 旧事件 | 字段映射 |
|---------------|---------------|---------|
| `TextDelta(text, block_index)` | `{"type": "text_delta", "text": text}` | block_index 丢弃（OpenAI compat 单 text block） |
| `ReasoningDelta(text, block_index, ...)` | `{"type": "reasoning_delta", "text": text}` | 其他字段丢弃 |
| `ToolCallStart(index, call_id, name, ...)` | （不直接映射） | 标准事件用于生命周期表达；旧路径原本不会发 start-only 心跳 |
| `ToolCallIdDelta(index, call_id)` | （不直接映射） | 旧路径只有 name/arguments 非空时才 emit；id 后到先更新 session 状态 |
| `ToolCallNameDelta(index, name_delta)` | `{"type": "tool_use_delta", "tool_use_id": <last_known_id>, "index": index, "name_delta": name_delta, "arguments_delta": None}` | name 后到时补发 |
| `ToolCallArgsDelta(index, delta, call_id)` | `{"type": "tool_use_delta", "tool_use_id": call_id or "", "index": index, "name_delta": None, "arguments_delta": delta}` | args 心跳，**关键不能丢** |
| `ToolCallEnd(...)` | （不映射，shim 内部转成 legacy_dict["content"] 中的 `tool_use` block） | |
| `ReasoningSignature` / `ReasoningBlockEnd` | （OpenAI compat 不会有） | 无 |
| `UsageUpdate` | （shim 累积到 legacy_dict["usage"]） | |
| `TurnDone` | （shim 转成 legacy_dict 整体返回） | |
| `ErrorEvent` | （shim 转成 raise，不直接 emit） | |

**约束**：
1. `tool_use_delta` 的 `tool_use_id` 字段在现有前端 V2 状态机里被消费做 action 关联——shim 必须保证一旦 id 已知就开始用真值
2. `arguments_delta` 是 chat-like 心跳信号，长 args 期间必须持续 emit（不能等聚合）
3. Phase 1A 为保持 `claude_client.create_streaming_turn` 行为 0 变化，shim 在正常结束后仍按旧路径 emit 终态 `reasoning` / `text` / `tool_use`；engine 继续过滤 text/reasoning，只消费 tool_use 和返回 dict
4. 同一 raw chunk 内相邻的 `ToolCallNameDelta` + `ToolCallArgsDelta` 要重组为一个 legacy `tool_use_delta`，匹配旧实现中 `name_delta` 和 `arguments_delta` 可同时存在的 payload

### 11.6.3 OpenAICompatParserSession 完整状态机伪代码（v6 替换 v5 的占位符）

```python
# agent_runner/model_adapter/openai_compat.py

class OpenAICompatParserSession:
    """完整等价复刻 claude_client.py:213-300 的所有行为。

    跨 chunk 状态：
      - text_buffer: 累积 delta.content
      - reasoning_buffer: 累积 delta.model_extra.reasoning_content
      - tool_calls_by_index: dict[int, {id, name, args_buffer, encoding="native_json"}]
      - usage: 最后非空 chunk 的 usage
      - finish_reason: 最后非 None 的 finish_reason
      - first_chunk_seen: bool（用于 first_chunk_timeout 判断）
      - turn_done_emitted: bool（防 finalize 重复）
    """

    def __init__(self, profile: ResolvedModelProfile):
        self.profile = profile
        self.text_buffer = ""
        self.reasoning_buffer = ""
        self.tool_calls_by_index: dict[int, dict] = {}
        self.usage: UsageUpdate | None = None
        self.finish_reason: str | None = None
        self.first_chunk_seen = False
        self.turn_done_emitted = False

    def feed(self, chunk) -> Iterable[StandardEvent]:
        # 1. usage-only chunk（流尾，没有 choices 但有 usage）
        if hasattr(chunk, "usage") and chunk.usage:
            parsed = _normalize_usage(chunk.usage)
            if parsed.input_tokens or parsed.output_tokens:
                self.usage = UsageUpdate(
                    input_tokens=parsed.input_tokens,
                    output_tokens=parsed.output_tokens,
                    total_tokens=parsed.total_tokens,
                )
                yield self.usage

        if not chunk.choices:
            return  # usage-only chunk 已处理

        delta = chunk.choices[0].delta
        if chunk.choices[0].finish_reason:
            self.finish_reason = chunk.choices[0].finish_reason

        # 2. reasoning_content（delta.model_extra）
        extra = getattr(delta, "model_extra", None) or {}
        rc = extra.get("reasoning_content", "")
        if rc:
            self.reasoning_buffer += rc
            yield ReasoningDelta(text=rc, block_index=0)

        # 3. text content
        if delta.content:
            self.text_buffer += delta.content
            yield TextDelta(text=delta.content, block_index=0)

        # 4. tool_calls 增量（关键：心跳 + id/name 后到）
        if delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in self.tool_calls_by_index:
                    # 首次见到这个 index，emit ToolCallStart
                    initial_id = tc_delta.id or None
                    initial_name = (tc_delta.function.name
                                    if tc_delta.function and tc_delta.function.name
                                    else None)
                    self.tool_calls_by_index[idx] = {
                        "id": initial_id or "",
                        "name": "",
                        "args_buffer": "",
                        "encoding": "native_json",
                    }
                    yield ToolCallStart(
                        index=idx,
                        call_id=initial_id,    # 可能是 None
                        name=initial_name,     # 可能是 None
                        encoding_hint="native_json",
                    )

                entry = self.tool_calls_by_index[idx]

                # id 后到（OpenAI compat 网关常见情况）
                if tc_delta.id and tc_delta.id != entry["id"]:
                    entry["id"] = tc_delta.id
                    yield ToolCallIdDelta(index=idx, call_id=tc_delta.id)

                # name 后到或重复发送完整 name：沿用旧实现的赋值语义，不拼接
                if tc_delta.function and tc_delta.function.name:
                    name_delta = tc_delta.function.name
                    entry["name"] = name_delta
                    yield ToolCallNameDelta(
                        index=idx,
                        name_delta=name_delta,
                        call_id=entry["id"] or None,
                    )

                # args 增量（核心心跳）
                if tc_delta.function and tc_delta.function.arguments:
                    args_delta = tc_delta.function.arguments
                    entry["args_buffer"] += args_delta
                    yield ToolCallArgsDelta(
                        index=idx,
                        delta=args_delta,
                        call_id=entry["id"] or None,
                    )

    def finalize(self) -> Iterable[StandardEvent]:
        """流结束（finish_reason 已知或 stream 自然 EOF）。
        构造 ToolCallEnd（每个 tool）+ TurnDone。
        """
        if self.turn_done_emitted:
            return
        self.turn_done_emitted = True

        # 1. 每个 tool_call 在终态做 JSON 解析，emit ToolCallEnd
        completed_blocks: list[StandardContentBlock] = []
        if self.reasoning_buffer:
            completed_blocks.append(ReasoningBlock(text=self.reasoning_buffer))
        if self.text_buffer:
            completed_blocks.append(TextBlock(text=self.text_buffer))
        for idx in sorted(self.tool_calls_by_index.keys()):
            entry = self.tool_calls_by_index[idx]
            raw_args = entry["args_buffer"]
            try:
                parsed = json.loads(raw_args) if raw_args else {}
                parse_error = None
            except json.JSONDecodeError as e:
                parsed = None
                parse_error = str(e)
            yield ToolCallEnd(
                call_id=entry["id"], name=entry["name"], index=idx,
                encoding="native_json", raw_args=raw_args,
                parsed_input=parsed, parse_error=parse_error,
            )
            if parsed is not None:
                completed_blocks.append(ToolUseBlock(
                    id=entry["id"], name=entry["name"], input=parsed,
                ))
            else:
                completed_blocks.append(InvalidToolCall(
                    id=entry["id"], name=entry["name"],
                    raw_args=raw_args, parse_error=parse_error,
                    index=idx, encoding="native_json",
                ))

        # 2. 映射 finish_reason → 标准 stop_reason
        stop_reason = _map_finish_reason(self.finish_reason)

        yield TurnDone(
            stop_reason=stop_reason,
            content=completed_blocks,
            text_blocks=[b for b in completed_blocks if isinstance(b, TextBlock)],
            reasoning_blocks=[b for b in completed_blocks if isinstance(b, ReasoningBlock)],
            tool_calls=[
                StandardToolCall(id=b.id, name=b.name, input=b.input, encoding="native_json")
                for b in completed_blocks if isinstance(b, ToolUseBlock)
            ],
            invalid_tool_calls=[b for b in completed_blocks if isinstance(b, InvalidToolCall)],
            sources=[],
            # Phase 1A：没收到 usage chunk 时保持 None，legacy response 再转成 {}
            usage=self.usage,
            provider_state=None,
            raw_stop_reason=self.finish_reason or "",
        )

    def finalize_on_error(self) -> Iterable[StandardEvent]:
        """transport 异常时：emit 已累积的 reasoning/text 给前端看到部分内容，
        但**不 yield TurnDone**（数据不完整）。tool_calls 中途的也不 yield ToolCallEnd
        （JSON 不完整 parse 也没意义）。"""
        # 故意不发 ReasoningDelta/TextDelta（已经在 feed 时发过了）
        # 故意不发 TurnDone（incomplete）
        return iter([])  # 阶段 1 简化版：什么都不发，让 engine 知道是异常路径
```

### 11.6.4 测试覆盖（L2 必跑）

| 场景 | 期望 |
|------|------|
| 单 text chunk → finish_reason=stop | TextDelta + finalize(TurnDone, stop) |
| reasoning_content 增量 + content 增量混合 | ReasoningDelta + TextDelta 顺序保留 |
| 单 tool_call: id 在第一个 chunk 给，name 在第二个 chunk 给 | ToolCallStart(call_id=id,name=None) + ToolCallIdDelta + ToolCallNameDelta |
| 单 tool_call: name 在第一个 chunk 给，id 在第二个 chunk 给 | 同上但顺序反 |
| 并行 tool_calls (index=0, index=1 交错) | 各 index 独立维护 args_buffer，各自 ToolCallEnd |
| tool args JSON parse fail | ToolCallEnd(parse_error 非 None) + InvalidToolCall 入 content |
| usage-only 末尾 chunk | UsageUpdate emit，TurnDone.usage 正确 |
| 流中途断（无 finish_reason）| finalize_on_error() 不 yield TurnDone，engine 走重试 |
| empty response（finish_reason=stop 但没 content）| TurnDone(content=[], stop_reason=stop) |

---

## 12. 附录 A：现有 4 处 reasoning_content 改动 → 新架构下哪里处理

| 原改动位置 | 新架构处理点 |
|----------|------------|
| `claude_client.py` 读 `delta.model_extra["reasoning_content"]` | Phase 1A：`OpenAICompatParserSession.feed()` 内 yield `ReasoningDelta` 并累积到 `TurnDone.reasoning_blocks` |
| `claude_client.py:_build_oai_messages` 塞回 | 阶段 1：`OpenAICompatAdapter.build_request()` 继续从 legacy dict 的 `reasoning_content` 序列化到 OpenAI message；Phase 2 再切到 `StandardMessage/ReasoningBlock` |
| `engine.py` ask_user / closing 合成 | 阶段 1 不动；Phase 2 才改为构造 `StandardMessage(content=[..., ReasoningBlock(...)])` |
| `project.py` + `project_service.py` 持久化 | Phase 1B 已做 `metadata_json["reasoning_blocks"]` 与 legacy `reasoning_content` 双读双写 |

**架构改进**（v5 修正表述）：
- 改造前：reasoning 处理散落在 4 处（claude_client × 2 + engine + project/project_service）
- Phase 1A：先把 `claude_client.py` 内的协议翻译收敛到 adapter（`build_request` + `parser session`），engine 和 persistence 保持原样
- Phase 1B：持久化层做 `reasoning_blocks` ↔ legacy `reasoning_content` 双读双写兼容，engine 仍保持 legacy dict
- Phase 2：再让 engine 只构造 `StandardMessage`

实质改进不是减少触点数，而是**触点的内聚性**：每一处只关心自己的职责，不再有"engine 知道 DeepSeek 协议细节"这种泄漏。

---

## 13. 附录 B：业界参考

**LangChain `BaseChatModel`**
- `langchain_core/language_models/chat_models.py`
- `langchain_core/messages/ai.py`
- **借鉴**：能力挂模型实例/profile，不挂 provider 类；保留 `tool_call_chunks`/`invalid_tool_calls`/`response_metadata`

**LiteLLM**
- `litellm/llms/custom_llm.py`
- **借鉴**：不假装一个薄协议永远够用；为 Responses API 保留单独入口

**Vercel AI SDK `LanguageModelV1`**
- **借鉴**：provider 只做边界工作；返回值保留 `providerMetadata`/`sources`/`response.id`/`reasoningDetails`

---

## 14. 附录 C：不在本方案范围

- 流控/key 池化/重试策略独立重构
- Observability：每个 adapter 的 latency / error rate / token 成本打点
- A/B test 框架：同模型对比网关 vs 原生
- 多 adapter 并行请求（投票/最快返回）
- 幂等层（对接 Responses API idempotency key）
- **structured output validation 框架**（agent 工具/结果的 JSON Schema 校验）—— 独立立项
- **隐私/system prompt 泄漏防护**（XmlStreamFilter scrub 策略）—— 独立立项，**注意不是模型适配层职责**
- **prompt assembly 层 context dedup**（XML tag 重复块去重）—— 独立立项

---

## 15. 附录 D：selfagency/llm-stream-parser 借鉴决议（v3 新增）

**项目**：https://github.com/selfagency/llm-stream-parser
**评估时间**：2026-04-25；v7 复核时间：2026-04-30
**克隆位置**：/tmp/llm-stream-parser
**项目状态**：Public TypeScript / Node 18+ 项目，GitHub 页面显示 0 stars / 0 issues / 171 commits；npm 包 `@selfagency/llm-stream-parser` 当前 `version=0.1.5`。README 明确列出 normalizers 覆盖 OpenAI、Anthropic、Gemini、Mistral、Cohere、Ollama、AWS Bedrock、HF TGI。

### 15.1 ✅ 吸收的设计

| 来源 | v3 落点 | 说明 |
|------|---------|------|
| `XmlToolCall.format` 三种编码 | `StandardToolCall.encoding` + `ToolCallStart.encoding_hint` | XML bare / json-wrapped / native-json 区分 |
| `XmlStreamFilter` 流式 XML parser + nesting depth 限制 | `ProtocolLimits.max_xml_nesting_depth` | 用于 XML thinking tags + XML tool calls 解析 |
| `validateJsonSchema` 深度/key 限制 | `ProtocolLimits.max_json_depth` | tool args JSON 解析深度护栏 |
| `ProcessorOptions` 资源限制思路 | `ProtocolLimits` 独立 dataclass + `ModelCapabilities.max_tool_calls_per_turn` | 但拆成"协议层硬护栏"+ "Profile 业务策略"两层，避免大 options |
| `LLMStreamProcessor` thinkingTagMap 配置 | `ThinkingExtractionConfig.mode = xml_tag` + open_tag/close_tag | DeepSeek-R1 系列在文本里嵌 `<think>` 标签的场景 |
| 多 provider normalizer 覆盖面 | Phase 1A/1B 的 characterization test matrix | 借鉴它按 provider 做输入归一化测试的思路，但本项目保持事件无损和 legacy 行为锁 |

### 15.2 ❌ 不吸收的设计（含理由）

| 来源 | 不吸收理由 |
|------|---------|
| `anthropic.ts` thinking 字符串化（丢 signature） | **反面教材**。selfagency 把 `thinking_delta.thinking` 直接 push 到 `chunk.thinking`，没处理 `signature_delta`。v3 必须比它做得好——见 §4.1.1 状态机。 |
| 单一扁平 `StreamChunk { content?, thinking?, tool_calls?, ... }` | 类型混乱，无法表达事件顺序和 block 生命周期。v3 用 sum type（`StandardEvent` union）。 |
| `ProcessorOptions` 70 行黑盒 | 配置项不分职责（模型/解析/scrub/安全/warning 全混）。v3 拆成 ModelCapabilities + ProtocolLimits + 运行时策略三层。 |
| `repairWithLLM` / `autoRepair` JSON 自动修复 | **silent fallback 危险**——把"坏参数"变成"猜出来的参数"会引入隐 bug。v7 继续保持显式 `parse_error`，把坏参数作为 `InvalidToolCall` 一等公民上抛。 |
| `dedupeXmlContext` XML 标签重复块去重 | 这是 prompt assembly 层职责，不该进 model adapter core。误用会丢上下文。 |
| `XmlStreamFilter` 隐私 scrub 标签策略 | system prompt 防泄漏是独立问题，应在响应清洗管道做，不和模型协议绑定。附录 C 已列为独立立项。 |
| `recovery/snapshot` & continuation prompt | 不是 v3 需要的 replay log。v3 的 StreamRecorder（§Step 1.2.5）是真正适合 adapter 灰度的录放工具。 |
| malformed XML/tool call 静默丢弃 | 本项目的 adapter 不能 silent drop。Phase 1A 对 malformed native tool args 已用 `input_parse_error` 保留到 legacy content；Phase 1B 继续用 `InvalidToolCall` 表达。 |

### 15.3 关键经验教训

1. **selfagency 项目代码质量不低，但协议设计不无损**——证明这条路上"看起来对"的方案也可能有 P0 问题。v3 必须比它做得好。
2. **不要照搬 ProcessorOptions 这种巨型 options 对象**——分层（协议护栏 vs 业务策略 vs 运行时配置）比统一 options 容易演进。
3. **JSON auto-repair 是反诱惑**——adapter 层就该让坏 JSON 显式失败，让上层决策怎么处理。
4. **normalizer 的测试矩阵值得借鉴，返回类型不要照搬**——我们的核心需求是多模型平台的无损返回，不能把不同 provider 的事件生命周期压成一个扁平 chunk。

---

## 16. Codex Review 记录

### 16.1 第一轮 Codex review（v1 → v2，2026-04-25 上午）

吸收的 P0 + P1 反馈：
- ✅ P0: reasoning 改 blocks（含 signature/redacted/provider_data）
- ✅ P0: capabilities 下沉到 Profile
- ✅ P0: 持久化分层（MessageView + ConversationState），engine_state_json 阶段 1 不动
- ✅ P1: 协议补齐 StandardToolCall/InvalidToolCall/ProviderState/Source/ErrorEvent
- ✅ P1: Adapter 拆 build_request/parse_stream_chunks + Transport 独立
- ✅ P1: 阶段 1 采用 shim 模式，不拆 engine
- ✅ P1: 补 ImageBlock/CacheMarker（标记阶段 1 非目标）
- ✅ P2: 风险表补齐 partial retry / lease mid-turn / JSON parse error / 事件顺序约束
- ✅ 评审问题新增 4 个关键问题

### 16.2 第二轮 Codex review（v2 → v3，2026-04-25 晚上）

**v3 修正的 P0 错误（v2 文档真实有问题）**：
- 🔴 §8 风险表 #7 与 §10 Q10 对 partial retry 描述自相矛盾 → §10 Q10 锁定决议，#7 配合修正
- 🔴 v2 把 Anthropic `signature_delta` 写成 `thinking_delta.provider_data` 的子字段 → 错的。v3 §4.1.1 重写状态机：signature_delta 是独立 SSE 事件，按 index 状态机聚合

**v3 修正的 P1 设计**：
- 🟡 v2 的 `encoding` 该放哪里没写 → v3 主真相源 `StandardToolCall.encoding`（终态）+ `ToolCallStart.encoding_hint`（诊断）
- 🟡 v2 没明确 thinking 提取协议 → v3 加 `ThinkingExtractionConfig` sub-schema
- 🟡 v2 没区分协议层硬护栏 vs 业务策略 → v3 引入 `ProtocolLimits`
- 🟡 v2 阶段 1 范围模糊 → v3 明确收窄到 OpenAI compat shim only

**v3 新增（v2 完全没有的）**：
- 🆕 §Step 1.2.5 StreamRecorder & Event Replay 工具
- 🆕 §4.1.1 Anthropic thinking block 状态机规格
- 🆕 §4.3 ThinkingExtractionConfig + ProtocolLimits
- 🆕 §14 selfagency/llm-stream-parser 借鉴决议

**Codex 评定 v3 状态**：可启动阶段 1（仅 OpenAI compat shim + characterization tests），不可同时承诺阶段 2。

**未完全采纳的 Codex 建议**：
- Codex 建议阶段 1 可以缩范围到"仅 OpenAI compat 归一化，明确不承诺跨协议"。**v3 实际上已经按这个建议做了**——阶段 1 只承诺 OpenAICompatAdapter，阶段 2 严格 gate 在 Anthropic PoC 完成后。

### 16.3 第三轮 Codex review（v3 → v4，2026-04-25 深夜）

**v4 修复的 P0 错误（v3 仍有的硬伤）**：
- 🔴 **`TurnDone` 丢 content block 顺序**：v1/v2/v3 都犯的错，分组聚合 text_blocks/reasoning_blocks/tool_calls 天生丢失 Anthropic thinking → text → tool_use 交错顺序。v4 加 `TurnDone.content` 作为主真相源，分组字段降级 view。
- 🔴 **Anthropic redacted_thinking 协议错了**：v3 状态机伪代码用 `{"thinking": text}` 回传 redacted。Anthropic 真实协议是 `{"type": "redacted_thinking", "data": "..."}`，且 data 是加密 blob 不是文本。v4 `ReasoningBlock.data` 字段 + 状态机正确处理。
- 🔴 **阶段 1 shim 双切点矛盾**：v3 Step 1.3 说在 `create_streaming_turn` shim，Step 1.4 又说 `_call_llm_with_retries` 切到 StandardEvent。v4 锁定**仅 Step 1.3 一个切点**，Step 1.4 删除。

**v4 修复的 P1 设计**：
- 🟡 partial retry 残余矛盾扫尾：§5.2 伪代码、§8 #13、§10 Q10 全部对齐"阶段 1 闭合状态重发整轮，partial 仅打点"
- 🟡 Anthropic tool_use 状态机伪代码补 `block_index → call_id` 真实映射，不再有 `call_id="?"` 占位
- 🟡 `ToolCallStart.name` 改可选 + 新增 `ToolCallNameDelta`（OpenAI streaming id 先到 name 后到的真实场景）
- 🟡 `ThinkingExtractionConfig.must_roundtrip` 默认值修正为 False（v3 默认 True 反了）
- 🟡 `ProtocolLimits` 补 `max_json_keys` + `max_total_stream_bytes`；transport vs adapter 执行边界明确
- 🟡 `StandardMessage.content` 唯一主真相源，删顶层 `reasoning_blocks` 字段
- 🟡 `stop_reason` 标准协议统一 `"tool_use"`，legacy `"tool_calls"` 仅在 shim 兼容层映射
- 🟡 `ToolCallEnd` 补完整字段（name/index/encoding/raw_args），InvalidToolCall 由它派生

**v4 新增（v3 完全没有的）**：
- 🆕 §11 capabilities 迁移规则：`resolve_capabilities` + `resolve_adapter_kind` 从现 flat 字段构造新结构
- 🆕 阶段 1 shim 实施时的 `_to_legacy_stop_reason` 兼容映射函数（tool_use → tool_calls）

**Codex 评定 v4 状态**：在 v3 review 基础上补完 P0+P1，可以提交团队评审；阶段 1 实施前最后清单见 §16.3 末尾。

**未完全采纳的 Codex 建议**：
- Codex 提到"`reasoning_view()` / `text_view()` 派生方法可能有性能问题"——v4 保留这两个方法但加 docstring 说明仅做 convenience，不是热路径。生产代码应该直接遍历 content。
- Codex 建议加 `max_total_stream_bytes` 在 transport 层。v4 已加到 ProtocolLimits 但执行点说明放在 transport 层（注释而非独立类）。

**阶段 1 实施前最后清单**（按 Codex 建议整理）：
- ✅ shim 单切点已锁（Step 1.3）
- ✅ TurnDone.content 主真相源已加
- ✅ stop_reason 标准/legacy 映射已写
- ✅ ThinkingExtractionConfig 默认值已修
- ✅ StreamRecorder 切点设计已补（先抽 legacy parser 纯函数，再录制）
- ✅ ProtocolLimits.max_json_keys 已加
- ✅ transport 异常 vs StandardEvent 责任边界已明确
- ✅ ToolCallStart.name 已改可选
- ⚠️ XML thinking tag 状态机细化（可选，DeepSeek-R1 时再做）
- ⚠️ CI fixtures 与生产私有 fixtures 分层（可选，StreamRecorder 实施时再定）

### 16.4 第四轮 Codex review（v4 → v5，2026-04-25 凌晨）

Codex 发现 v4 有一个**架构级 P0**和 2 个内容级 P0，以及若干 P1。v5 全部修复。

**v5 修复的架构级 P0**：

🔴 **`parse_stream_chunks(iter([raw_chunk]))` per-chunk 调用模式会丢跨 chunk 状态**

这是 v1-v4 都犯的隐蔽错。文档伪代码两处都这样写：
```python
async for raw_chunk in transport.stream(...):
    for event in adapter.parse_stream_chunks(iter([raw_chunk]), profile):
        ...
```

每个 raw_chunk 单独构造 iterator 喂进去 → adapter 内部 `tool_state` / `block_kinds` 累加器**每次都重置**。症状：
- text-only 看起来正常
- L1/L2 单元测试用整段 chunks 喂能通过
- 只有 tool args 分片 / 并行 tool / Anthropic blocks 才爆——**生产环境才发现**

v5 重新设计接口：`StreamParserSession` stateful session，每个 turn 一个实例，按 `feed(chunk)` 增量推送，session 内部维护状态。adapter 提供 `create_parser_session()` 工厂方法。

**v5 修复的其他 P0**：

🔴 **redacted_thinking 的 `data` 字段没贯穿全链路**：v4 类型加了 `data` 但 accumulator/TurnDone/build_request 三处伪代码仍按 `thinking` 处理。v5 完整状态机：accumulator 在 `content_block_start` 把 `cb["data"]` 存进 reasoning_state，`ReasoningBlock` 携带到 build_request，build_request 对 `redacted=True` 输出 `{"type":"redacted_thinking","data":data}`，绝不写 `thinking` 字段。

🔴 **transport exception 闭合语义未定**：v5 明确——transport 抛 exception → engine 捕获后 emit `assistant_turn_ended(reason="error", incomplete=True)` 闭合前端状态机，然后重发整轮（重复 delta 业务上可接受）。session 提供 `finalize_on_error()` 给已累积事件的优雅 emit。

🔴 **ProtocolLimits 超限信号自相矛盾**：v4 一边说 "adapter 不能伪造 ErrorEvent"，一边说"超限上抛 ErrorEvent"。v5 选定**超限抛 transport/parser-level exception**，不进 StandardEvent。engine 收到后 emit `assistant_turn_ended(reason="protocol_limit", incomplete=True)`，且不重试（异常 payload 重试也撞）。

**v5 修复的 P1**：

🟡 `ToolCallStart.call_id` 改可选 + 新增 `ToolCallIdDelta`：OpenAI streaming 不只 name 可能后到，id 也可能后到。session 用 `index` 作为内部主键，id/name 由 IdDelta/NameDelta 后续补充。

🟡 `InvalidToolCall` 加入 `StandardContentBlock` union：`TurnDone.content` 是主真相源时必须保留 invalid tool call 的原始顺序，靠旁路 `invalid_tool_calls` 列表无法保证。

🟡 `TextDelta` 加 `block_index`：Anthropic 一个消息可能有多个 text block 与 thinking/tool_use 交错，事件流必须能区分属于哪个 text block。

🟡 `resolve_capabilities` 函数（§11）补字段映射注解：从现 `model_profile.py` 真实字段名（`supports_function_calling` 等）映射到新 `ModelCapabilities`，不再含糊。

**v5 一致性修复**：
- 附录 A "4 处 → 2 处" 表述更正：实质改进不是减少触点数，是触点的内聚性
- §16.3 末尾 "可启动阶段 1" 改为 "v4 仍有架构级 P0，v5 修完才可启动"

**Codex 评定 v5 状态**（预期，待第五轮确认）：
- parser stateful session + redacted data 贯穿 + transport exception 闭合 三大 P0 已修
- 阶段 1 应可启动（仅 OpenAICompatAdapter shim + characterization tests）
- 阶段 2（Anthropic native）启动门槛保持不变：thinking 状态机 PoC + StreamRecorder 工具 + 1 周灰度

**v5 仍有未解决的可选项**：
- XML thinking tag 模式（DeepSeek-R1）状态机细化
- CI fixtures vs 生产私有 fixtures 分层策略
- Responses API 的 `previous_response_id` TTL 策略
- Gemini grounding sources 的前端展示约定

这些是 v6 / 阶段 2 启动前再处理。

### 16.5 第五轮 Codex review（v5 → v6，2026-04-26）

Codex 评定 v5 仍 not-ready，找到 4 个 blocker + 多个 P1。v6 全部修复 + 调整重点。

**v6 修复的 P0**：

🔴 **shim exception 闭合错放层级**：v5 在 `create_streaming_turn` shim 内部直接 emit `assistant_turn_ended` 是错的——shim 没有 `turn_id/message_id`（那些是 engine 的），retry 时会和 engine 外层的闭合事件**重复**。v6 shim 只 emit assistant_stream 级事件 + raise，engine 层 catch 后做 lifecycle 收尾。新增 §11.5 异常路径时序图把这套语义画出来。

🔴 **`OpenAICompatParserSession` 完整规格**：v5 只有三个方法名占位符。v6 §11.6 补完整状态机伪代码（180+ 行），等价复刻 `claude_client.py:213-300` 所有 legacy 行为：
- usage-only chunk 跳过 choices 但保留 usage
- `delta.model_extra.reasoning_content` 取 reasoning
- tool delta 即刻 emit `ToolCallStart/IdDelta/NameDelta/ArgsDelta` 心跳
- id 后到时补 `ToolCallIdDelta`
- finalize 时聚合 `TurnDone(content=[...])` 保留顺序

🔴 **`ToolCallArgsDelta` 加 `index`**：v5 只带 `call_id` 必填，但 OpenAI streaming id 后到时无法归属。v6 改 `index` 必填、`call_id` 可选。

🔴 **`resolve_capabilities` 字段映射对齐真实代码**：v5 写 `overrides.get("supports_tool_use")`，但 `model_profile.py:27` 真实字段是 `supports_function_calling`。v6 严格按真实代码字段名映射，含 `tool_call_style="native"` → 标准 `"openai_native"` 的标准化转换。

**v6 修复的 P1**：

🟡 §4.1.1 状态机 accumulator 补 `data` 字段（v5 实现里有，规格漏写）
🟡 `StreamParserSession` Protocol 加 `finalize_on_error()` 声明（v5 调用了但接口没声明）
🟡 ProtocolLimits 超限和 transport exception 区分（§11.5.3）
🟡 redacted data 缺失从 silent skip 改 `raise InvariantError`
🟡 `tool_call_style` 值域和真实 profile 对齐

**v6 范围调整（按 Codex 建议）**：

🔵 **Anthropic native adapter 降级为"阶段 2 PoC 草图"**：在 Step 2.1 开头加显眼标注，明说不要在阶段 1 实施时按这段写代码。Codex 指出当前草图至少缺 `message_start` / `ping` / `error` / citations 事件处理——阶段 2 启动时按 PoC 实测重写。

🔵 **新增 §11.5 异常路径时序图**：完整画出 `transport exception → engine catch → emit assistant_turn_ended → retry 决策` 的责任分工
🔵 **新增 §11.6 OpenAI compat → legacy event 映射表**：StandardEvent → 现 SSE 事件的逐项映射，作为 L2 characterization test 对齐基准

**Codex 评定 v6 状态**（待第六轮 review 确认）：
- 4 个 P0 已按建议修
- OpenAICompatParserSession 完整规格已补
- 阶段 1 实施前最后清单见 §11.5 + §11.6
- 阶段 2 Anthropic native 仍需 PoC 实测才能动手

**v6 仍未完全解决的可选项**：
- XML thinking tag 模式（DeepSeek-R1 早期）状态机
- StreamRecorder 的 fixture 分层和录制工具落地
- Anthropic 真实 PoC（含 message_start/ping/error 等遗漏事件）
