# Agent Core 全面审核报告 — Phase B 三件套

> **审核日期**：2026-05-29
> **审核范围**：Phase B 活跃三件套
> - `packages/rd-agent-contracts`（跨包协议层，3031 行）
> - `packages/rd-agent-core`（host-neutral turn/run kernel，1063 行，审核时全部未提交）
> - `packages/rd-llm-adapter`（LLM provider 适配，2278 行）
> **审核维度**：架构 / 正确性 / 安全 / 测试
> **审核方法**：9 个审查单元（package × 维度）并行 fan-out → 每条发现独立 skeptic agent 对抗证伪 → 跨单元去重分级。共 66 个 agent、2391 次工具调用。
> **测试基线**：195 passed, 18 skipped, 0.18s（纯单元测试，无 E2E）。
> **统计**：原始 56 条发现 → 对抗验证后存活 32 条 → 去重后 **23 条有效问题**（证伪剔除 24 条臆测）。

---

## Executive Summary

**总体结论：架构健康，存在 1 个计费正确性缺陷必须修，其余多为防御性编程与文档化欠缺。**

| 维度 | 健康度 | 结论 |
|------|--------|------|
| **架构 / host-neutral 边界** | ✅ 健康 | core 不依赖 SaaS/FastAPI/SQLAlchemy，跨包依赖方向单向无环（contracts ← core ← llm-adapter，contracts 零反向依赖），`test_architecture_boundaries.py` 强制约束生效。无 P0/P1 架构违规。 |
| **正确性** | ⚠️ | 1 个 P1 计费缺陷（cache token 字段映射丢失），其余为边界与并发场景的防御缺口（P2/P3）。 |
| **安全** | ✅ | 无真实漏洞。被报的 SSRF / 工具白名单 / schema 校验经验证均为 host-neutral 库的**责任边界委托**（应由 SaaS 宿主层负责），降级为 P2/P3。 |
| **测试** | ⚠️ | 单元测试扎实（195 passed），但缺独立集成链路串联测试 + 无覆盖率门槛。18 个 skip 经核实是**有意的依赖隔离**而非功能缺口（详见末节）。 |
| **依赖卫生** | ⚠️ | 3 项依赖声明问题（pydantic / anthropic 完全未使用，httpx / openai 应为可选）。 |

**优先行动建议**：

1. **P1-1**（含 P2-5 同源）cache token 修复应最先处理（计费正确性）。
2. 清理 **P2-11/12/13** 三项依赖（低风险快速收益）。
3. **P2-1/4/6/7/8** 文档化 + 测试补强可批量跟进。
4. 所有 **P3** 多为防御性编程与责任边界文档化，可在 B-3 重构窗口统一处理。

---

## 🔴 P1 — 必须修复

### P1-1. Cache token 字段映射丢失 `cache_creation_input_tokens`，影响计费准确性

- **维度**：correctness
- **位置**：
  - `packages/rd-agent-core/src/rd_agent_core/turn.py:390-397`（`_usage_from_update`）
  - 上游链路 `packages/rd-llm-adapter/src/rd_llm_adapter/anthropic_native.py:305-307`
  - `packages/rd-llm-adapter/src/rd_llm_adapter/_usage.py:31-32,116`
- **证据**（已人工核实代码两端）：
  - Anthropic adapter (`anthropic_native.py:305-307`) 将 `cache_read_input_tokens` 与 `cache_creation_input_tokens` **求和**合并进单一字段 `UsageUpdate.cached_input_tokens`：
    ```python
    cached_input_tokens = int(
        _field(raw_usage, "cache_read_input_tokens", 0) or 0
    ) + int(_field(raw_usage, "cache_creation_input_tokens", 0) or 0)
    ```
  - `_usage_from_update()` (`turn.py:393-396`) 仅把该合并值映射到 `Usage.cache_read_input_tokens`：
    ```python
    return Usage(
        input_tokens=update.input_tokens,
        output_tokens=update.output_tokens,
        cache_read_input_tokens=update.cached_input_tokens,
    )
    ```
  - 结果：`Usage.cache_creation_input_tokens` 永远为 0。
  - 契约层 `packages/rd-agent-contracts/src/rd_agent_contracts/usage.py:16-17` 明确定义了两个独立 cache 字段，下游 `run.py` 的 `_add_usage`、`run_persistence.py`、`test_usage.py:38` 都按两个字段消费。
  - cache creation 与 cache read 在多数 provider 计费费率不同（Anthropic 写入约 1.25×、读取约 0.1×），合并后下游 Meter 无法正确归因成本。**零测试覆盖该字段映射。**
- **建议**：在 adapter 层就保留两类 cache token 的区分——给 `UsageUpdate` 增加独立字段（`cache_read_input_tokens` / `cache_creation_input_tokens`），停止在 `_usage.py:116` 的求和合并；`_usage_from_update` 分别映射两个字段。这是契约级决策，影响计费准确性，需优先处理。修复需同时改 adapter 与 contracts 两层。
- **备注**：此条由 `contracts-correctness` 与 `core-correctness` 两个单元独立报出（P1），并与 P2-5「normalization pipeline 求和」为同一根因的上下游两端，已合并。

---

## 🟡 P2 — 应修复

### P2-1. 续跑 `turn_offset` 缺文档与校验，可能导致 turn_index 重复
- **维度**：correctness
- **位置**：`packages/rd-agent-core/src/rd_agent_core/run.py:57,117`
- **证据**：`turn_index = request.turn_offset + len(turn_results) + 1`（:117）。`turn_offset: int = 0`（:57）无校验，`RunRequest` 无 `__post_init__`。contracts 层 `run_persistence.py:174` 存在 `create_continuation_run()`，说明续跑是预期场景。`turn_index` 会落入事件日志（`turn.py:123` 的 `TURN_STARTED` payload）。若续跑时宿主忘记设置 `turn_offset`，turn_index 会从 1 重启，造成跨续跑边界的重复索引。零测试、零文档。
- **建议**：在 `RunRequest.turn_offset` 与 `RunKernel.run()` 上文档化续跑契约，或提供从上一轮 `turn_results` 计算 offset 的 helper；考虑加校验钩子。

### P2-2. `ReasoningBlock.data` 缺编码/校验规范
- **维度**：architecture
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/transcript_blocks.py:38-50`
- **证据**：`data: str | None`（:49）注释为「Anthropic redacted_thinking 的加密 blob」，但无 `__post_init__` 校验 `redacted=True ↔ data is not None`，无编码说明（base64/raw），无序列化往返保证。不变量目前由 adapter 层强制（`anthropic_native.py:372-386` 在 data 为空时抛 `ValueError`），dataclass 为 frozen，且 `ReasoningBlock` 仅由 adapter 构造，因此实践中被 adapter 架构兜底。
- **建议**：在 dataclass 层加自校验 `__post_init__`（redacted 时要求 data 非空），明确编码约定（base64？raw bytes？）以支撑 saas-adapter 的 byte-equal 保留需求。

### P2-3. 重复工具调用 guard 的跨 turn 可变列表缺文档
- **维度**：architecture
- **位置**：`packages/rd-agent-core/src/rd_agent_core/run.py:104,119-122,223`
- **证据**：`tool_signatures: list[ToolCallSignature] = []`（:104）在 while 循环外创建，每个 turn 创建新 `_RepeatedToolCallGuard` 但共享同一列表引用，`self._signatures.append(candidate)`（:223）跨 turn 累积。该设计有意且经测试（`test_run_kernel.py:269-323`），但 `RunKernel.run()` / `_guarded_tool_executor` / `_RepeatedToolCallGuard` 均无 docstring 解释为何列表必须跨 turn 持续，对未来维护者脆弱。
- **建议**：在 `RunKernel.run()` 加 docstring 说明跨 turn 追踪意图；考虑用 `_RepeatedCallTracker` 包装裸列表使意图显式。

### P2-4. USAGE_UPDATE 事件缺 idempotency_key，partial-retry 场景无去重
- **维度**：correctness
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:286,179`、`run.py:148`
- **证据**：`turn.py:286` 是唯一缺少 `idempotency_key` 的流式核心事件：`return writer.append(CoreEventType.USAGE_UPDATE, event.to_dict())`，对比 `turn_started`/`tool_started`/`turn_completed` 都带 key。`run.py:148` 的 `_add_usage(usage, turn_result.usage)` 累加 usage。若同一 `turn_id` 被重复调用 `run_turn`，USAGE_UPDATE 会重新生成且 EventLogPort 无法识别为重复，导致重复计数。当前 `run.py` 每轮生成新 turn_id 不触发，但这是对调用层的隐式假设而非协议强制。
- **建议**：为 USAGE_UPDATE 增加格式化 idempotency_key（如 `{turn_id}:usage`）；在 UsageUpdate/TurnDone 增加 sequence_number 以支持去重，并补 stream-retry 去重测试。

### P2-5. 流式 partial-retry 场景 cache token 求和导致区分丢失（adapter 层设计错位）
- **维度**：correctness
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/_usage.py:31-32,116`
- **证据**：`_ALIASES` 将 `cache_read_input_tokens` 与 `cache_creation_input_tokens` 都映射到 `cached_input_tokens`，`:116` 处 `mapped[canonical] = mapped.get(canonical, 0) + value_int` 求和。这是有意行为（与 `anthropic_native.py:305-307`、`openai_compat.py:218` 一致），但 contracts 层保留区分而 adapter 层抹除，形成架构错位。
- **建议**：与 P1-1 同源——若需保留区分，修改 `UsageUpdate` 为独立字段并更新 normalization；若有意合并，则文档化原因。**与 P1-1 一并修复。**

### P2-6. `build_messages_after_turn` 缺 tool_use_id 一致性验证（测试覆盖缺口）
- **维度**：testing
- **位置**：`packages/rd-agent-core/src/rd_agent_core/run.py:228-274`、`tests/test_run_kernel.py:369-382`
- **证据**：`run.py:258` 用 `zip(tool_calls, tool_results, strict=True)` 按位置配对。当前顺序由构造保证（`turn.py:158` 按 `turn_done.content` 顺序遍历执行），实际不会错配。但测试 `test_build_messages_after_turn_pairs_tool_results` 仅检查 count 与单个 tool_name/tool_use_id，**未显式断言** `tool_calls[i].id == tool_results[i].tool_use_id` 的整体对应关系，隐式排序契约未文档化、未验证。开发者若改动 `turn.py:158` 的遍历顺序，现有测试无法捕获。
- **建议**：加 `test_build_messages_after_turn_preserves_tool_use_id_consistency` 显式验证 ID 配对；考虑在 `build_messages_after_turn` 返回前加 ID 一致性校验循环。
- **备注**：原建议「按 `ToolExecutionResult.tool_use_id` 匹配」在技术上不可行——`tool_execution.py:43-48` 的 `ToolExecutionResult` **不含** tool_use_id 字段，需先在返回结构中建立映射。

### P2-7. timeout 边界与精度的测试覆盖不足
- **维度**：correctness/testing
- **位置**：`packages/rd-agent-core/src/rd_agent_core/run.py:82-91`、`tests/test_run_kernel.py:237-267`、`policies.py`
- **证据**：`>=` 比较逻辑（`policies.py:57`）本身正确。但 `test_run_kernel_checks_timeout_before_followup_turn`（:237-267）只用 `ticks=(100.0, 100.0, 100.2)` 测了 0ms 和 200ms 两个极端，缺 `elapsed_ms == timeout_ms` 边界与毫秒 `int()` 截断的近边界精度测试。（`timeout_ms=0` 因构造时校验 `policies.py:26-27` 被拒，属有意设计，非缺陷。）
- **建议**：加 `test_run_kernel_blocks_on_exact_timeout_boundary` 与毫秒精度测试。

### P2-8. `StreamParserSession.finalize_on_error` 中间态恢复未实现且无测试
- **维度**：testing
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/anthropic_native.py:131-132`、`tests/test_model_adapter_anthropic_native.py:371-384`
- **证据**：`AnthropicNativeParserSession.finalize_on_error()` 当前实现为 `return iter(())`，无论会话状态都返回空。但设计文档 `docs/MODEL-ADAPTER.md:1074-1082` 明确规定该方法「可以 yield 部分 TextBlock / ReasoningBlock 信息」。`has_partial_output` 属性（:85-86）及 `text_buffers`/`reasoning_state`/`tool_state` 状态已维护但未利用。现有测试只验证立即错误，缺「feed 到一半 + error」的中间态场景。
- **建议**：实现 `finalize_on_error` 的部分输出 yield，并加 `test_anthropic_parser_partial_stream_error_recovery`（feed text → feed tool_start → feed error → finalize_on_error 验证不崩溃且返回清理后的 partial）。

### P2-9. OpenAI compat 解析器接受非 dict JSON 时静默转空 dict
- **维度**：correctness
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/openai_compat.py:327-342`（关键在 :329）
- **证据**：`parsed_input = parsed if isinstance(parsed, dict) else {}`（:329）。合法但非 dict 的 JSON（数组、字符串）会被静默转成空 dict 并仍 emit `ToolUseBlock` 而非 `InvalidToolCall`，丢失原始结构信息。原建议的「adapter 层 schema 校验」架构上不可行（parser session 仅接收 `profile` 不接收 tools，:204），schema 校验应在 executor 层。
- **建议**：将非 dict JSON 视为 `InvalidToolCall`（保留 raw arguments）而非静默转空 dict。

### P2-10. 集成链路缺独立串联测试（18 skip 掩盖三个集成点）
- **维度**：testing
- **位置**：`packages/rd-llm-adapter/tests/test_model_adapter_engine_golden.py:34-38`、`test_model_adapter_openai_compat.py:48-52`、`test_model_adapter_recorded_fixtures.py:30-35`
- **证据**：18 个 skip 中 11 个为 engine golden（依赖 codesphere-saas 的 AgentEngine），7 个为 create_streaming_turn 集成 + recorded fixture 回放。核心函数（`build_request`、`OpenAICompatParserSession.feed/finalize`、`legacy_response_from_turn_done`、`terminal_events_from_turn_done`）**已有无 skip 的单元测试覆盖**，缺的是不借助真实 `create_streaming_turn` 的**完整流程串联** E2E 测试。
- **建议**：在 rd-llm-adapter 包内建独立集成测试：(1) 用 spy-transport/recorded fixtures 重现 `create_streaming_turn` 完整流程；(2) 将 engine golden 核心 scenario 用 assert-based replica 迁移到包内（不依赖 AgentEngine）；(3) 为 recorded fixtures 建 CI-friendly mock data。短期可用 pytest-recording/betamax 保存真实 HTTP trace。
- **备注**：原报 P1，对抗验证降为 P2——因核心功能已有单元覆盖，并非「关键功能完全无覆盖」。

### P2-11. 未使用依赖 `pydantic` 声明于 rd-agent-contracts
- **维度**：architecture
- **位置**：`packages/rd-agent-contracts/pyproject.toml:7`
- **证据**：声明 `pydantic>=2.7`，但 src+tests 全量 grep 零导入（无 BaseModel/Field/ConfigDict），全部类型用 stdlib dataclasses（17 处 `from dataclasses import`）。contracts 层应零运行时依赖。
- **建议**：移除该依赖。

### P2-12. 未使用依赖 `anthropic` 声明于 rd-llm-adapter
- **维度**：architecture
- **位置**：`packages/rd-llm-adapter/pyproject.toml:9`
- **证据**：声明 `anthropic>=0.40`，全 src grep 零 `from anthropic`/`import anthropic`，无懒加载。唯一引用是 `anthropic_transport.py:52` 的 URL 字符串字面量（非代码使用）。对比 OpenAI SDK 在 `transports.py:21` 正常导入。
- **建议**：移除该依赖；若为未来预留，移至 `[project.optional-dependencies]`。

### P2-13. 懒加载传输（httpx / openai）被标为必需而非可选
- **维度**：architecture
- **位置**：`packages/rd-llm-adapter/pyproject.toml:8,10`
- **证据**：`httpx>=0.27`、`openai>=2.0` 在必需依赖列表，但均在 try/except 中懒加载（`anthropic_transport.py:25` / `transports.py:21`），缺失时抛 helpful RuntimeError。
- **建议**：移至 `[project.optional-dependencies]`，标签如 `anthropic-transport` / `openai-transport`。
- **备注**：P2-11/12/13 三条同属依赖卫生（`cross-arch-leak` 单元），可一并清理 pyproject。

---

## 🟢 P3 — 建议改进 / 防御性编程

> 多为有意的 host-neutral 责任委托或文档欠缺，可在 B-3 重构窗口统一处理。

### P3-1. `build_subagent_outcome_json` 硬编码 schema_version "1.0"
- **维度**：correctness
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/subagent_runtime.py:184,416`
- **证据**：两处 `"schema_version": "1.0"`。这是 **outcome_json**（存储于 `SubagentTaskRecord`）的 schema，与 `AgentEvent` 的 canonical `SCHEMA_VERSION="1.2.0"` 是**不同概念**，各自独立版本号本身合理。但硬编码字面量无单一来源，测试也未验证该字段。
- **建议**：抽取为模块级常量，避免散落硬编码；补测试断言该字段。

### P3-2. `SCHEMA_VERSION` 常量在 events.py 与 __init__.py 重复，存在漂移风险
- **维度**：architecture
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/events.py:15` vs `__init__.py:167`
- **证据**：`_DEFAULT_SCHEMA_VERSION = "1.2.0"`（events.py:15）为避免循环 import 而本地定义，注释（:13-14）警告「升级时必须同步」。当前两值一致（`test_smoke.py:15` 验证），漂移会立即表现为功能问题。
- **建议**：抽 `_version.py` 单一来源模块，两边 import 消除手动同步。

### P3-3. `decide_subagent_workspace_isolation` 缺 docstring 说明决策语义
- **维度**：architecture
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/workspace.py:57-93`
- **证据**：函数无 docstring，三个 bool flag 有顺序优先级（:65-82），`workspace_isolation_enabled=False` + `agent_kind="subagent"` 返回 `enabled=False`（reason="workspace_isolation_disabled"）不报错。这是正确策略（`reason` 字段消歧），非「conflation」缺陷，仅文档欠缺。`workspace_isolation_enabled=False` 路径无测试。
- **建议**：加 docstring 说明顺序决策策略与 reason 字段语义；补 disabled 路径测试。

### P3-4. `ContinuationJobRecord.attempts` 语义未文档化、无校验
- **维度**：correctness
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/continuation_queue.py:36-54`（:44 字段）
- **证据**：`attempts: int` 无 docstring 说明计「started/completed/failed」哪种，无 `__post_init__` 校验 `attempts <= max_attempts`。原发现「attempts 永远 0 卡死」不准确（`0 >= 1` 为 False 会走 release_for_retry，非 DEAD_LETTER）。真实问题仅是语义模糊 + 缺校验，外部实现 port 时易出错。
- **建议**：文档化 attempts 计数语义；加 `__post_init__` 校验。

### P3-5. `TurnKernelResult.provider_state` 捕获后从未消费
- **维度**：architecture
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:79,212`、`run.py:144,172`
- **证据**：`provider_state` 字段（:79）从 `turn_done.provider_state`（:212）赋值，但 `run.py` 中从未读取，累积入 `turn_results` 无消费者。`openai_compat.py:378` 总是 `None`。看似为 B-3 重构预留。当前是 None 占位符，不构成「无声增长大对象」。
- **建议**：若未用则移除保持抽象干净；若未来宿主需要用于恢复，明确文档化并加 run.py 消费逻辑。

### P3-6. idempotency_key 用 turn_id 裸字符串拼接，turn_id 含冒号时可能碰撞
- **维度**：correctness
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:126,152,175,199,238,247,299,357`
- **证据**：key 形如 `f'{request.turn_id}:...'`，假设 turn_id 不含冒号。默认 `UuidIdGenerator`（`run.py:89`）产生 `turn_{uuid4}` 无冒号（`test_ids.py:19` 确认），故默认路径安全。但 `TurnRequest` 无 `__post_init__` 校验（:47-57），自定义 IdGenerator 或直接构造含冒号 turn_id 时可碰撞。
- **建议**：在 `TurnRequest.__post_init__` 拒绝含 `:` 的 turn_id，或对 turn_id 做 URL 编码后拼接。

### P3-7. subagent 工具白名单未在 core kernel 强制（host-neutral 委托）
- **维度**：security
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:303-312`
- **证据**：`TurnKernel._execute_tool()` 只校验 `declared_tool_names`（来自 `request.tools`），不校验 subagent profile 白名单。`filter_subagent_tools_for_profile()` / `subagent_profile_allows_tool()`（`subagent.py:262-282`）在 core 中从未调用。这是**有意的 host-neutral 设计**——kernel 期望宿主通过 `BusinessToolProviderPort.list_tools()` 预过滤，`ToolExecutionContext` 不含 `agent_profile`，kernel 无法在执行时解析 profile。在 kernel 强制会违反 host-neutral 原则。
- **建议**：文档化「宿主必须用 `filter_subagent_tools_for_profile()` 预过滤」的契约，并加测试验证该要求；不在 kernel 内强制。

### P3-8. LLM tool 参数未做 JSON schema 校验（防御纵深缺口）
- **维度**：security
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:334`
- **证据**：`tool_input=dict(tool_call.input)` 直接传给 executor，未对 `ToolDefinition.input_schema`（:303-304 可得）做校验。adapter（`anthropic_native.py:232-237`）只校验 JSON 解析。全库零 jsonschema 导入。属架构委托（fail-closed boundary，:341 注释），executor 层应负责校验；kernel 侧 schema 校验是防御纵深增强而非必须。
- **建议**：可选地在 kernel 加 schema 校验（有 input_schema 时校验 tool_call.input，失败返回 `ok=False` + schema_validation_error），或文档化由 executor 负责。

### P3-9. 工具可观测性记录存储原始 tool_input 未脱敏（host 责任）
- **维度**：security
- **位置**：`packages/rd-agent-core/src/rd_agent_core/turn.py:377`
- **证据**：`tool_input=tool_call.input` 原样存入 `ToolObservabilityRecord` 无脱敏。这是**有意设计**——脱敏委托给宿主 `PolicyGate.redact_event`（`ports.py:49-59`）与宿主的 `ToolObservabilityPort` 实现；core 无语义知识判断哪些字段敏感；tool_output 同样未过滤（对称处理）。在 core 加 pattern 脱敏架构上不正确。
- **建议**：在宿主 `ToolObservabilityPort` 实现中做脱敏；文档化该责任边界。

### P3-10. RunKernel 循环终止部分依赖未验证的 LLM stop_reason（日志注入风险）
- **维度**：security
- **位置**：`packages/rd-agent-core/src/rd_agent_core/run.py:158-164`
- **证据**：原发现的主论点「stop_reason 控制循环终止」**不成立**——循环终止完全由 kernel-controlled 的 `pause_requested` 与 `tool_calls_executed` 控制（:163-164），stop_reason 仅用于事件记录。真实问题是 `anthropic_native.py:413` / `openai_compat.py:391` 返回未验证字符串写入事件 payload（`turn.py:187`），属数据验证/日志注入风险。
- **建议**：对 stop_reason 做白名单校验（end_turn/tool_use/stop/length/content_filter 等）后再写入。

### P3-11. subagent 委托决策无输入大小限制（理论 DOS / 性能）
- **维度**：security
- **位置**：`packages/rd-agent-contracts/src/rd_agent_contracts/subagent_delegation.py:132-199`
- **证据**：`decide_subagent_delegation` 对 instruction/message 文本无大小校验（:147-162），消息上限 10 条（`[-10:]`，:159）。`:187` 在同一表达式重复 `term.lower()` 与 `signal_text.lower()`，加 6 次 `_contains_any` 共约 24 次 `.lower()` 调用，若传入多 MB 字符串则重复昂贵操作。原报 O(m*n) 复杂度描述不准（m、n 均常量），真实问题是大字符串上的重复操作。无证据当前被对抗输入调用。
- **建议**：加输入长度上限（如 instruction 10KB、signal_text 总长上限），用编译 regex 替代重复 `.lower()`，加决策预算/超时。

### P3-12. `UsageRecord.__add__` 的 total_tokens 计算逻辑错误（死代码）
- **维度**：correctness
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/_usage.py:88-89`
- **证据**：`total_tokens=(self.total_tokens + other.total_tokens) or (...fallback...)`。`UsageRecord(total=15) + UsageRecord(total=0)` 得 `(15+0) or (...) = 15`（应为 20），`or` 在第一操作数 truthy 时短路阻止 fallback。`__add__` 未导出（不在 `__all__`），全库无调用，当前是**死代码**，不会在生产执行。
- **建议**：改为 `total_tokens=(self.input_tokens+other.input_tokens)+(self.output_tokens+other.output_tokens)`，移除 fallback。

### P3-13. OpenAI compat `tool_calls_by_index` name 字段初始化不对称
- **维度**：correctness
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/openai_compat.py:270-272`
- **证据**：`:271` `"id": initial_id or ""` 用了提取值，`:272` `"name": ""` 硬编码忽略 `initial_name`。当前**无功能 bug**——若提取到 initial_name 则 function_delta 必非 None，name_delta 会在同循环 :293-295 赋值。属对未来重构脆弱的一致性问题，非正确性 bug。
- **建议**：`:272` 改为 `"name": initial_name or ""` 与 id 模式对齐。

### P3-14. Anthropic base_url 传给 httpx 未做 SSRF 校验（库责任边界）
- **维度**：security
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/anthropic_transport.py:37-42`
- **证据**：`anthropic_messages_url()`（:49-67）只做路径标准化无 netloc 校验，理论上 base_url 指向内网会 SSRF。Phase B 是 host-neutral 库无用户输入机制，base_url 来自业务适配器（SaaS 层，不在审核范围），所有测试用受信值。SSRF 防护应由调用端负责。属责任边界问题。
- **建议**：若未来库需自防护，在 `anthropic_messages_url()` 早期校验 netloc 白名单（拒绝 localhost/私网段/metadata IP）；否则文档化由调用端负责 URL 校验。

### P3-15. Anthropic API 错误消息未脱敏直接抛出
- **维度**：security
- **位置**：`packages/rd-llm-adapter/src/rd_llm_adapter/anthropic_native.py:120-123`
- **证据**：`raise RuntimeError(message)`，message 来自 API 响应未脱敏（`test:374` 确认有意行为）。Anthropic 错误消息受信，几乎无密钥泄露风险，实际是对 MITM 代理污染的防御纵深考量。该模块无 logger，message 仅出现在异常 trace。
- **建议**：将完整消息记 debug 日志，抛出脱敏版本（如 `Anthropic stream error: type=...`），防御理论上的日志注入/信息泄露。

### P3-16. `repeated_tool_call_threshold` 的 0/负值在 guard 层未防御
- **维度**：correctness
- **位置**：`packages/rd-agent-core/src/rd_agent_core/policies.py:19-27`、`run.py:193-202,209`
- **证据**：`RunLimits.__post_init__` 校验 `threshold >= 1`（:26），但 `_RepeatedToolCallGuard.__init__`（:193-202）与 `has_repeated_tool_call`（:82-84）假设 `threshold >= 1` 而不自校验。frozen dataclass 可被 `object.__setattr__` 绕过，若 threshold=0 则 `:209` 条件恒真阻断所有工具调用。无外部反序列化路径，需内部刻意篡改触发，属深度防御。
- **建议**：在 `_RepeatedToolCallGuard.__init__` 与 `has_repeated_tool_call` 开头加 `assert threshold >= 1` 或抛 ValueError；补 0/负值边界测试。

---

## 覆盖与盲区

### 审得透的部分
- **架构边界（高置信）**：`cross-arch-leak` + `core-arch` 单元全量读取三包源码（contracts 24 文件、core 6 文件全读、adapter 关键文件深读），grep 验证跨包依赖单向无环，确认 core 无 SaaS/FastAPI/SQLAlchemy 导入。`test_architecture_boundaries.py` 在测试期强制约束。**无 P0 架构违规**，host-neutral 设计落地扎实。
- **turn/run kernel 正确性**：`core-correctness` + `contracts-correctness` 全读 turn.py/run.py/policies.py 并跑通 26 个单元测试，逐行核查状态机、工具执行流、pause/repeated-guard 逻辑、idempotency、事件顺序、消息构建。cache token 缺陷是此处最实质的发现。
- **依赖卫生**：通过 AST + grep 全面核对依赖声明 vs 实际使用，3 项依赖问题证据确凿。

### 盲区
- **真实 E2E / 集成链路**：18 个 skip 对应的 AgentEngine golden、create_streaming_turn 完整流、recorded fixture 回放**在本仓库无法独立运行**。包内单元测试用 in-memory mock，**无法暴露 stream/retry 场景**的边界问题（P2-4 usage 去重、P2-7 timeout 精度、P2-8 partial-error 恢复都属此类）。
- **adapter 内部深处**：`recorder.py`(578 行)、`base.py` 部分、anthropic/openai parser 的并发/取消路径未逐行覆盖。
- **并发/线程安全**：仅逐行审视可能竞态，未实测多进程/并发环境。
- **business.py（rd-agent-core）adapter 模式**：作为契约定义未深审；经验证其 port 当前**未被 kernel 调用**（纯契约），故 P3-7/8/9 的安全委托结论成立。

### 18 个 skip 的真实风险结论
**18 个 skip 不是隐藏的功能缺陷，而是有意的依赖隔离设计**（测试文件注释明确依赖 codesphere-saas 私有模块）。被 skip 的集成测试所覆盖的核心函数（build_request、parser feed/finalize、legacy_response/terminal_events 转换）在包内**均有无 skip 的单元测试覆盖**。

**真实风险在于「集成链路串联」无独立信号**：单元测试验证了各组件的局部正确性，但 adapter↔transport↔legacy bridge 的端到端串联、fixture 回放一致性、partial-stream error 恢复这三条链路目前只能依赖 SaaS 端的 golden trace 验证。一旦这些 skip 在 SaaS 集成时解除，由于 **pyproject 无覆盖率门槛配置**，无法强制覆盖检查防止回归。建议（P2 级）：在包内补建不依赖 SaaS 的集成测试 + 配置覆盖率门槛，将 skip 的「外部依赖隔离」与「真实未覆盖逻辑」彻底分离。

---

## 附：审核方法说明

本报告由多 agent workflow 编排生成：

1. **审查阶段**（9 个并行单元）：contracts×{架构,正确性}、agent-core×{架构,正确性,安全}、llm-adapter×{正确性,安全}、跨包×{测试}、跨包×{架构泄漏专项}。每个单元用 Explore agent 实际 Read/Grep 代码并产出带 `file:line` 证据的结构化发现。
2. **对抗验证阶段**：每条发现交独立 skeptic agent，要求实际读引用代码尝试**证伪**（误读/引用不符/实为设计取舍/已被覆盖/严重度夸大）。原始 56 条 → 证伪剔除 24 条 → 存活 32 条。
3. **综合阶段**：跨单元去重、按修正后严重度重新分级、产出本报告。

P1-1（唯一 P1）已由人工二次核实代码两端确认为真缺陷。
