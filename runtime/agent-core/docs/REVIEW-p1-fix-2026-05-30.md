# P1-1 修复批次评审报告

> **评审日期**：2026-05-30
> **评审对象**：针对 `AUDIT-phase-b-2026-05-29.md` 中 P1-1（及连带 P2/P3）的修复批次
> **评审方法**：6 个主题单元并行评审（每单元双重目标：① 验证修复是否正确闭环 ② 揪出新引入的回归/缺陷）→ 每条质疑独立 skeptic 对抗证伪 → 去重分级。50 个 agent、1587 次工具调用。原始 43 条质疑 → 证伪剔除 21 条 → 存活 22 条（其中多数为「对正确修复的确认」，真正待办见下）。
> **关键结论经主会话人工实机复现验证**（P2-A 往返放大、测试数字、不可达性判断）。

---

## 1. 总体结论

**✅ 可以接受，建议补 2 项测试后合入（无阻断问题）。**

P1-1 cache token 计费缺陷已**真正修好且全链路闭环**（已实机验证）：

```
anthropic_native._merge_usage (拆分提取 read/creation)
  → UsageUpdate / UsageRecord (两独立字段 + __post_init__ 双向兼容)
  → turn._usage_from_update (turn.py:415-420 分别映射)
  → contracts.Usage (usage.py:14-17 两字段)
```

全程不混合、不合并。附带的 P2-9 / P3-12 / P3-13 / P3-2 / P3-1 等修复均正确。

**测试基线（主会话权威实测）**：`207 passed / 18 skipped`（107 contracts + 70 adapter + 30 agent-core）。
> ⚠️ 评审 agent 报告的「177」漏算了 rd-agent-core 的 30 个测试（因该目录 git untracked）。权威数字为 **207**。

本批次改动文件 ruff 全部 clean。唯一需开发者跟进的是 `_usage.normalize_usage` 的一处**潜在（当前生产不可达）序列化往返放大缺陷**及对应回归测试缺口——不阻断合入，但应在接通真实计费链路前补齐。

---

## 2. 逐修复主题判定表

| 主题 | 判定 | 一句话结论 |
|------|------|-----------|
| **cache token 核心** | ✅ CORRECT | P1-1 数据流 adapter→events→turn→contracts 完整闭环，实机验证 read/creation 独立保留，`__add__` 与 `_merge_usage` 累积/合并语义均正确。 |
| **cache token 测试** | ⚠️ CORRECT_WITH_NITS | 关键路径有测试（parser 保留 cache 拆分，回退旧代码会失败），但缺 `__add__` cache 聚合测试、序列化往返测试。 |
| **adapter 行为变更** | ✅ CORRECT | P2-9 两 adapter 一致地把非 dict JSON 工具参数转 `InvalidToolCall`；P3-13 `initial_name or ""` 向后兼容；无 breaking change（语义修正型变更，建议 CHANGELOG 标注）。 |
| **contracts 重构** | ✅ CORRECT | `_version.py` 单一来源 `SCHEMA_VERSION="1.2.0"`、`__version__=1.13.0` 与 pyproject 同步、零 pydantic、`SUBAGENT_OUTCOME_SCHEMA_VERSION` 常量化、managed_agent 4 符号导出，全部验证通过。 |
| **其余 P2/P3** | ✅ CORRECT | continuation_queue 校验、ReasoningBlock invariant、workspace docstring、rd-llm-adapter 依赖 optional 化，均对症且测试通过。 |
| **跨切面（序列化/recorder/全局）** | ⚠️ CORRECT_WITH_NITS | 核心闭环、recorder 向后兼容跳过新字段正确；但暴露一处潜在往返放大缺陷（见 P2-A）。 |

---

## 3. 待办问题（跨单元去重，按修正严重度）

> 原始存活质疑中，绝大多数标 P0/P1 的项经逐条核实实为**对正确修复的确认**（reasoning 实为「无需修改」），不构成待办。下表只列真正需要开发者动作的项。

### 🟡 P2

#### [P2-A] `_usage.normalize_usage` 对自身 `to_dict()` 输出做往返会放大 cache_read（潜在，当前生产不可达）
- **类型**：residual / design-fragility
- **位置**：
  - `packages/rd-llm-adapter/src/rd_llm_adapter/_usage.py:31`（`_ALIASES["cached_input_tokens"] → "cache_read_input_tokens"`）
  - `_usage.py:90-104`（`to_dict` 同时输出 `cache_read_input_tokens` 与兼容字段 `cached_input_tokens`）
  - `_usage.py:143-148`（别名循环 `mapped[canonical] = mapped.get(canonical,0) + value_int` —— **累加**而非覆盖）
- **证据（主会话实机复现）**：
  ```
  UsageRecord(cache_read_input_tokens=10).to_dict()
    → {cache_read_input_tokens: 10, cached_input_tokens: 10}
    → normalize_usage(...) → cache_read_input_tokens = 20   ❌ 翻倍

  UsageRecord(read=3, creation=5).to_dict()
    → {..., cache_read_input_tokens: 3, cache_creation_input_tokens: 5, cached_input_tokens: 8}
    → normalize_usage(...) → cache_read = 11 (3 + 8)         ❌ 放大
  ```
  根因：`to_dict` 同时序列化新字段和兼容字段，别名循环把兼容字段 `cached_input_tokens` 累加到 `cache_read` 上而非覆盖。
- **为何不阻断（已核实生产不可达）**：无任何生产路径把 `_usage.to_dict()` 喂回 `_usage.normalize_usage()`：
  - `_usage.normalize_usage` 只在 `openai_compat.py:218` 对**原始 provider chunk** 调用；
  - `recorder.py` 不 import `normalize_usage`，只做 JSON 序列化不反向重建；
  - `run_persistence.py:108` / `rd-llm-gateway/normalizer.py:115` 用的是 **contracts 的** `normalize_usage`（`usage.py:23-35`，无累加、不读 `cached_input_tokens`），往返安全。
  - ⚠️ **脆弱点**：`openai_compat.py:572` 的 `legacy_response_from_turn_done` 会调 `UsageUpdate.to_dict()`（同样输出新+旧字段）。若未来下游把该 legacy usage 接回任一 adapter 层 `normalize_usage`，缺陷即被激活。
- **建议**（任选其一）：
  1. 别名循环对 cache 字段改「覆盖/取较大值」而非累加；
  2. `to_dict` 不再同时输出 `cached_input_tokens`（消费方都已读拆分字段）；
  3. 至少加注释 + 一条往返测试锁定行为，防止未来踩雷。

#### [P2-B] 回归测试缺口（3 项）
- **类型**：test-gap
- **位置**：`packages/rd-llm-adapter/tests/test_usage.py`
- **缺口**：
  1. `UsageRecord.__add__` 未断言 cache_read/creation 求和（`_usage.py:116-122` 有逻辑无覆盖，逻辑经实机验证正确）；
  2. `to_dict() → normalize_usage()` 往返一致性未测 —— 正是 P2-A 会暴露的路径；
  3. 非 dict 工具参数 invalid + valid **混合**在同一 turn 的隔离性未测（`anthropic_native.py:271-296` 逻辑正确但无测试，重构易回归）。
- **建议**：新增 `test_usage_record_add_with_cache_tokens`、`test_usage_record_roundtrip_serialization`（顺带固化 P2-A 结论）、`test_*_invalid_and_valid_tool_calls_mixed`。

### 🟢 P3 — nits（不影响合入，可顺手清理）

| # | 标题 | 类型 | 位置 | 说明 |
|---|------|------|------|------|
| P3-a | cache 回退三处条件不对称 | inconsistency | `anthropic_native.py:312` vs `events.py:104` / `_usage.py:83` | 前者仅 `not cache_read_input_tokens`，后两者 `not (read or creation)`。**实机无害**（`_merge_usage` 随即构造 `UsageUpdate`，其 `__post_init__` 重算 `cached=read+creation` 兜底）。统一为 `not (read or creation)` 仅为防御一致性。 |
| P3-b | openai_compat 异常分支风格不一致 | inconsistency | `openai_compat.py:335-340` vs `anthropic_native.py:237` | 前者把 `(JSONDecodeError,TypeError)` 与 `ValueError` 拆成两个 body 相同的 except，后者合并为一。语义等价，建议合并消除重复。 |
| P3-c | `__all__` 中 ManagedAgent* 非严格字母序 | nit | `contracts/__init__.py:196-199` | 整列表本就非严格字母序，容忍范围内，可选。 |

### ✅ 已核实**不构成问题**（避免误判为待办）
- ❌ 「`__init__.py` 引入 ruff import-sort 违规」—— **证伪**：该文件 `ruff check` clean，本批的 import 重排实为**修正**既有乱序。
- ⓘ 全仓 `ruff check packages/` 确有 1 处 `I001`，但位于 **`trace.py`**（git status clean、git diff 空、上次改动是无关旧 commit `9570956`），属**本批次之外的既存问题**。若要全仓干净可顺手 `ruff --fix trace.py`，与本次评审无关。
- ❌ 多条「P0/P1 cache token 链路存活问题」—— 实为对正确修复的确认，无需动作。

---

## 4. 测试评估：回归测试是否足以锁定 P1-1 不复发？

**基本足够，补 2 项后完全锁定。**

- ✅ **核心锁定测试**：`test_anthropic_parser_preserves_cache_usage_breakdown`（`test_model_adapter_anthropic_native.py:254`）验证 `message_start(read=3,creation=5) + message_delta(无 cache)` → 最终 `to_dict()` 仍含 `read=3/creation=5` —— **回退旧合并代码会失败**，确实锁住 P1-1 主缺陷。集成层 `test_turn_kernel_streams_events_and_executes_completed_tool_call` 验证 `UsageUpdate(read=3,creation=5)` 正确流到 `result.usage`。`test_usage_record_add_computes_total_from_component_tokens` 锁住 P3-12。
- ⚠️ **缺口**（见 P2-B）：`__add__` cache 求和、`to_dict→normalize` 往返、混合 invalid/valid 工具调用三条未覆盖。往返测试尤为重要——它是 P2-A 的探针。
- **结论**：当前测试能防 P1-1 主路径复发；补齐 P2-B 三项后视为完全锁定。

---

## 5. 放行建议

**可合入，建议补 2 项后合入（无阻断、无需返工）。**

按优先级：

1. **（建议合入前）补 P2-B 的 3 条回归测试** —— 尤其 `to_dict→normalize` 往返测试，成本低、收益高。
2. **（建议合入前或紧随）处理 P2-A**：选「别名不累加 / to_dict 不重复输出 cached / 加注释+测试」之一。**此缺陷当前生产不可达不阻断本批**，但接通真实计费链路前必须解决。
3. **（可选随手）** 统一 P3-a 回退条件、P3-b 异常分支风格；`ruff --fix` 顺带清掉 `trace.py` 的既存 I001（与本批无关）。
4. **（文档）** CHANGELOG 标注 P2-9 行为变更：模型返回非 JSON 对象（数组/字符串等）的工具参数，现被识别为 `InvalidToolCall` 而非静默转空 dict。

---

## 附：关键证据文件

- `packages/rd-llm-adapter/src/rd_llm_adapter/_usage.py`（P2-A 根因 L31/L90-104/L143-148；`__add__` L106-124；`__post_init__` L80-88）
- `packages/rd-llm-adapter/src/rd_llm_adapter/events.py`（UsageUpdate L91-126）
- `packages/rd-llm-adapter/src/rd_llm_adapter/anthropic_native.py`（`_merge_usage` L299-330；P2-9 L232-239；P3-a L312）
- `packages/rd-llm-adapter/src/rd_llm_adapter/openai_compat.py`（P3-13 L275；P3-b L335-340；normalize 调用 L218；legacy usage to_dict L572）
- `packages/rd-agent-core/src/rd_agent_core/turn.py`（`_usage_from_update` L412-420，git untracked）
- `packages/rd-agent-contracts/src/rd_agent_contracts/usage.py`（Usage + contracts normalize_usage L12-35）
- `packages/rd-agent-contracts/src/rd_agent_contracts/_version.py`（单一来源 SCHEMA_VERSION）
- `packages/rd-llm-adapter/src/rd_llm_adapter/recorder.py`（向后兼容 skip；不 import normalize_usage）
