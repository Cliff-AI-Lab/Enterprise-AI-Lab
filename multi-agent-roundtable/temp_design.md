# TelegramAgent 架构草案 (temp_design.md)

> 状态：第 10 轮快照。Path C 端到端实证已跑通（sarah agent on ruidong-std/glm-5.1 全部 bootstrap 文件注入生效）。所有决定都可推翻。
> 文档目的：把"已对齐的判断"和"还没想清楚的口子"分开，避免下一轮讨论重复绕。

## 当前实证状态（第 13 轮）

| 能力 | 状态 |
|---|---|
| OpenClaw Gateway daemon 本地跑 | ✅ pid alive on `127.0.0.1:18789` |
| `openclaw.json` 含 `agents.list[main, sarah, alex, kai]` + ruidong provider | ✅ doctor 0 errors |
| Path C (`POST /v1/chat/completions` + `model: "openclaw/<id>"`) | ✅ 200 响应 |
| Workspace bootstrap (SOUL/AGENTS/USER/IDENTITY/TOOLS) 注入 | ✅ 全 3 visible agent 行为 case 通过 |
| Ruidong provider 接 OpenAI-compat | ✅ ruidong-std → glm-5.1；ruidong-plus → kimi-for-coding |
| 多 agent 共存 + 各自独立 session store | ✅ `~/.openclaw/agents/{main,sarah,alex,kai}/` 独立 |
| sessionKey 隔离（user 字段派生 + agentId namespace） | ✅ 5/5 跨 agent 隔离 case 通过 |
| 跨 agent 自我边界认知（"这事是 kai 的"） | ✅ 不依赖 main agent 调度，SOUL/AGENTS 自带 |
| **长期记忆 / memory_search** | ✅ bge-m3 接通 (`openai-compatible` provider, 1024 维)；sarah 主动调 memory_search 给出 source ref `memory/2026-05-30.md#L15` |

**最小可跑入口**：
- `scripts/verify-openclaw.mjs` — 单 agent 端到端 (sarah)
- `scripts/verify-multi-agent.mjs` — 4 agent + session 隔离
- `scripts/test-ruidong-direct.mjs` — 绕过 Gateway 直测 prompt 工程
- `openclaw memory status --deep` — 查 embedding/vector store ready 状态
- `openclaw memory index --force` — 改动 `personas/<id>/memory/*.md` 后重建索引

## 0. 产品定位（已对齐）

**"Telegram" 是 UI 风格参考，不是渠道。**

- 形态：**本地 Web 应用 (MVP)**，单用户
- 视觉风格参考 Telegram：联系人列表 / 简洁聊天界面 / 群组
- 反差点：**看起来是社交软件，实际是工作工具**
- Persona 偏职业向：写文案 / 财务 / HR / 法务 / PM ...（具体首发待定）
- 价值主张：用社交化的轻量感降低 AI 工具的使用门槛，让"AI 同事"比"ChatGPT prompt 工具"更亲近

**护城河方向：A + B 都要 (✅ 已定)**
- A. Persona-as-Coworker：人设饱满 + 单聊深度
- B. Multi-Agent 协作：群聊上帝模式 + 进化
- 接受 MVP 拖慢的代价，换产品差异化更立体

## 0.1 MVP 约束（已对齐）

- 单用户、本地运行
- Web 前端 + 本地后端 + OpenClaw 本地实例
- 无多租户、无认证规模问题、无部署故事
- 存储：本地 DB（SQLite 倾向）
- 所有 persona 实例都是"你的"，进化只来自你的互动

## 0.2 设计哲学（已对齐）

**UI 轻，能力深**：
- 界面永远保持 Telegram 风格的简洁，不做企业级管理面板
- 深度藏在 Skills / MCP / 工具栈里，用户感受不到技术复杂度
- 升级路径 = 打磨 persona (加 skill / 改 soul / 接更多 MCP)，不是堆 UI 功能

**SubAgent 模版必须可扩展**：
- 模版是模块化结构，不是一个大 prompt
- 加 skill / 加 MCP server / 换 model / 改 soul 都不应推翻模版
- 模版要支持版本化（evolution_log 是它的天然产物）
- Base + extensions 的组合模式，不同 persona 用不同组合

---

## 1. 核心架构（第 9 轮重大修订）

> 调研发现 OpenClaw 原生支持 `agents.list[]` 多 per-persona configured agent。第 1-8 轮的"Main spawn visible SubAgent"模型被推翻，改成"平级 configured agents"模型。详见 `openclaw_research.md §9.1`。

```text
┌─────────────────────────────────────────────────────────┐
│  Web 前端 (Telegram 风格)                                │
└─────────────────────────────────────────────────────────┘
                          ↕ HTTP / WS
┌─────────────────────────────────────────────────────────┐
│  我们的后端 (SQLite + 业务逻辑 + Orchestrator)           │
│  - users / rooms / messages / runs / artifacts          │
│  - agent_profiles (指向 personas/<id>/ 目录)            │
│  - room_orchestration / context_pack_snapshots          │
│  - permissions / audit_events / evolution.md            │
│  - 群聊调度逻辑（按需调 LLM，详见 §5.45.3）             │
└─────────────────────────────────────────────────────────┘
                          ↕ Path C: OpenAI HTTP /v1/chat/completions (MVP)
                          ↕ Path A: @openclaw/sdk (Phase 2)
                          @ http://127.0.0.1:18789
┌─────────────────────────────────────────────────────────┐
│  OpenClaw Gateway daemon (本地, channels 全关)           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ agents.list[] (配在 openclaw.json)              │   │
│  │   "main"   workspace=personas/main/             │   │
│  │   "sarah"  workspace=personas/sarah/   ← 写文案 │   │
│  │   "alex"   workspace=personas/alex/    ← PM     │   │
│  │   "kai"    workspace=personas/kai/     ← 工程师 │   │
│  │  每个 agent 独立: workspace / session store /    │   │
│  │  auth-profiles / model / sandbox / tools         │   │
│  │  tools.agentToAgent = enabled                    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          ↓ (按需) sessions_spawn
┌─────────────────────────────────────────────────────────┐
│  Worker Runs (临时后台任务, 不进 UI)                     │
│  - 由某个 visible agent 或 main spawn                    │
│  - 只加载 AGENTS.md + TOOLS.md, 没 SOUL.md               │
│  - 完成后 announce 回 requester                          │
└─────────────────────────────────────────────────────────┘
```

### 1.1 三类 agent 的清晰区分

| 类型 | 实现 | 用户可见 | 生命周期 | workspace 文件 |
|---|---|:---:|---|---|
| **Main Agent** | `agents.list[]` 一项 (id="main") | ❌ | 长期 | 全套 (SOUL/AGENTS/USER/...) |
| **Visible SubAgent** | `agents.list[]` 各一项 (sarah/alex/kai) | ✅ | 长期 | 全套 |
| **Worker Run** | `sessions_spawn` 拉的临时 sub-agent | ❌ | 单次 run | 只 AGENTS.md + TOOLS.md |

### 1.2 Main Agent 调度走两条路径之一

**路径 a（MVP 选）**：调度逻辑跑在**我们的后端**
- 群聊调度 / 选发言者 / 拼 ContextPack 都是 Node 代码
- 需要 LLM 决策时（§5.45.3 五个场景）通过 SDK 调 `main` agent
- 优势：可读、可调试、可加 SQL 日志、可单测

**路径 b**：Main Agent 作为 OpenClaw agent 自己调度
- 用 `tools.agentToAgent` 调 sarah/alex/kai
- 优势：纯 LLM 自主；劣势：调试黑盒

### 1.3 旧版架构图存档（避免下次思考又绕回来）

```text
[已废弃 — 第 1-8 轮]
Main Agent (单点) → spawn/resume (spawnAcpDirect) → visible SubAgent (raw sub-agent)
                                                  → spawn worker

问题: spawnAcpDirect 实为 ACP 外部 harness 通道；
visible SubAgent 走 raw sub-agent 会丢 SOUL.md；
"resumeSessionId only-spawner" 约束逼出复杂的"重生模式"。
改用 native multi-agent (§9.1) 全部消解。
```

---

## 2. 已对齐的判断

### 2.1 OpenClaw 角色定位
- **OpenClaw 是 runtime，不是产品内核**
- OpenClaw 负责：每个 configured agent 的 workspace / session / memory / tool runtime
- 我们的 DB 负责：用户身份、房间/成员、消息存档、permissions、audit、ContextPack snapshot、orchestration 状态

### 2.2 Visible SubAgent 生命周期 = OpenClaw configured agent（重写）
- **每个 persona (sarah/alex/kai) = `agents.list[]` 一项**，启动时配好就一直在
- 不需要 spawn / resume；用户打开聊天 → 后端通过 SDK 直调对应 agentId → OpenClaw 创建或复用 session
- Session 由 OpenClaw 自己管：daily reset (4am 本地) / idle reset / `/new` / `/reset` 都可控
- 状态映射（6 状态，对齐 GPT/CodeX 建议）：
  - `online` = configured 且 Gateway 跑着
  - `thinking` = 当前有 run 在生成
  - `working` = run 内调工具 / worker
  - `waiting` = 等用户审批
  - `away` = provider 限流 / 降级
  - `offline` = Gateway 没跑 / agent 被禁

### 2.3 私聊 vs 群聊介入模型（仍然成立）
| 场景 | Main agent 是否每条介入 | 理由 |
|---|---|---|
| 私聊 | 否 | 后端直路由到目标 agent；Main agent 不介入 |
| 群聊 | 是 | 后端调度逻辑 + 必要时 LLM 决策（§5.45.3）|
| 后台 | 是 | reflector loop，低频独立运行 |

### 2.4 群聊三种调度模式（仍然成立，机制更新）
- **依次** / **并行** / **Loop** 三种模式定义不变（§5.45.1）
- 实现：调度由后端代码控制；通过 SDK 调各 agent 的 run；按需调 Main agent 做 LLM 决策
- OpenClaw 提供的原语：`agentToAgent` tool / `sessions_send` / `sessions_history`

### 2.5 进化机制（大幅简化，删除"重生模式"）
- **不再需要"重生模式"**：直接改 `personas/<id>/SOUL.md` 等 workspace 文件即可
- 进化流程（MVP）:
  1. 后端 reflector loop 读 OpenClaw `sessions_history` + 我们的 messages 表
  2. LLM 提 diff，写入 `personas/<id>/evolution.md` (append-only changelog) + 文件改动提议
  3. 人审 gate（MVP 全人审）
  4. 批准后 patch 对应 workspace 文件
  5. 已经活的 session 不受影响，直到自然 reset 或 `/reset` 触发；新 session 自动加载新内容
- 紧急运行时替换可选：`agent:bootstrap` hook（MVP 不做）
- ~~`resumeSessionId` 复活旧 session~~ 不适用（每个 agent 各自有 session store）

---

## 3. OpenClaw 的硬约束（第 9 轮更新）

详细见 `openclaw_research.md §9.6`。重写后约束精简了很多：

| 约束 | 适用场景 | 影响我们 |
|---|---|---|
| ~~`resumeSessionId` 只原 spawner 恢复~~ | ACP 外部 harness only | **不影响**，我们不用 ACP |
| `subagentControlScope = children only` | sub-agent (sessions_spawn) | Worker Run 是黑盒，需 visible agent 主动 surface |
| 无共享 session / 房间原语 | 全部 | 仍然成立但不再阻塞：后端调度逻辑直接调各 agent 即可 |
| `AgentConfig` 启动时加载, 无 hot-reload | 全部 | 改 `openclaw.json` 要 `gateway restart`; workspace files 可走 `agent:bootstrap` hook 换 (MVP 不用) |
| `runTimeoutSeconds` 硬超时 | sub-agent / ACP | Worker Run 要设合理超时 |
| Sub-agent session 不加载 SOUL.md | sub-agent only | Worker Run 没人格；要塞 task 字符串 + 写进 AGENTS.md |
| Auth profiles 不跨 agent 共享 OAuth | multi-agent | 每个 agent 独立 auth-profiles.json；portable api_key 可拷 |

---

## 4. 还没想清楚的（按重要性排序）

### 4.1 群聊调度的 main agent 用什么模型？
- 每条群消息都触发 main agent，成本敏感
- 当前默认（第 10 轮）：main 与 sarah 同用 `ruidong/ruidong-std` (glm-5.1 backend)，验配置先用；正式 MVP 应区分
- 选项：
  - (a) 小快模型做调度，主力模型留给 subagent → ruidong 目录里没有便宜小模型；如果定调度独立，要外挂 deepseek/groq 等
  - (b) ruidong-plus (kimi-for-coding) 做调度兜底（cheaper），visible agent 继续 ruidong-std
  - (c) 规则优先 + LLM 兜底（轮数计数器先跑，规则定不了再叫 LLM）— 我们已经在 §1.2 路径 a 走这条
- **当前判断**：(c) 已经在架构层落地（拼 ContextPack / 选 sequential 下一发言者 / verdict 解析全是 Node 代码），LLM 只在 §5.45.3 五个场景被调；先不优化模型分层，等真实 group chat 数据出来再判
- **影响**：直接决定每条群消息的 latency 和 cost

### 4.2 ~~进化的审批 gate~~ ✅ 已定 (§5.5.5)
- MVP 全人审；Quality Signals 触发 + evolution.md 单一来源
- 自动 apply / 灰度逻辑 → Phase 2 候选 (§5.5.5a)

### 4.3 ~~Channel 入口~~ ✅ 已定
- 本地 Web 应用，OpenClaw 多 channel 不用
- 自己做 Web UI（Telegram 风格参考）

### 4.4 ~~AgentRuntime Adapter 接口要不要做？~~ ❌ 否决 (见"已评估并放弃")
- MVP 用 `runtime/openclaw.ts` thin client 替代抽象层

### 4.5 ~~Persona 模型~~ ✅ 已定 (§5.5 + §1.1)
- 首发 3 个 persona: sarah-writer / alex-pm / kai-engineer
- Each = OpenClaw configured agent；模版可扩展通过 4 个维度
- **演化可视化** (Sarah 学会你的语气) — 待定，phase 2 候选

### 4.6 Worker Run 可观测性 (仍开放)
- main agent 看不到 grandchildren；visible subagent (sarah/alex/kai) 触发 worker 跑研究 → main agent 怎么知道 worker 在干啥？
- 选项：visible subagent 自己回报进度到 DB；或 worker 直接写 artifact 到 DB
- 现在不紧急，但 §5.4.3 schema 的 `runs.parent_run_id` + `artifacts.source_run_id` 留了口子

### 4.7 ~~数据模型 schema 细节~~ ✅ 已定大头 (§5.4.3)
- 完整 DDL `schema.sql` 待写

### 4.8 ~~Permissions 模型~~ ✅ 已定 (§5.47)
- 三级风险 + Permission Gateway + `permission_grants` 表
- OpenClaw `tools.deny` 黑名单作为底层 + 我们 Permission Gateway 作为用户信任层

### 4.9 本地存储与 OpenClaw 数据边界 (更新)
- 我们 DB (SQLite)：room / message / agent_profiles / runs / artifacts / permission_grants / audit_events / context_pack_snapshots / user_facts
- 我们项目目录：`personas/<id>/` (workspace 文件 + evolution.md)
- OpenClaw 本地存储：`~/.openclaw/agents/<id>/agent/` (auth-profiles) + `sessions/` (transcript)
- 备份恢复：MVP 不解决，但 personas/ + DB 进 git 已够大头

---

## 5. 第一版 MVP 范围（建议）

> 这一节是建议，不是决定。下一轮可推翻。

```text
Must have (MVP):
- 本地 Web 应用 (后端 + 前端 + OpenClaw 本地实例 + SQLite)
- Telegram 风格轻 UI: 联系人列表 / 单聊 / 群聊
- 3 个职业向 persona: 写文案 / PM / 工程师
- 可扩展的 SubAgent 模版结构 (后续加 persona / 加 skill 不推翻)
- 1 个 main configured agent (隐藏 orchestrator, `agents.list[]` 一项), 同 sarah/alex/kai 平级
- 私聊跑通：单聊深度要够 (A 护城河)
- 群聊跑通：依次模式 + 上帝模式调度 (B 护城河)
- 持久化：persona 退出再回来，记忆还在
- 接 Skills/MCP 的基础设施 (让 persona 能干实事)

Nice to have (phase 2):
- 更多 persona / 用户自定义 persona (`openclaw agents add` 流程)
- 并行 / Loop 调度模式
- 后台 reflector loop + 进化机制
- 进化可视化 (让用户看到 persona "成长")
- Worker Run (`sessions_spawn`)
- EvolutionPatch DB 表 + 自动 apply 流程

Out of scope (MVP 不做):
- AgentRuntime Adapter 抽象 (拒绝, 已评估)
- 多用户 / 云部署 / 多租户
- Persona marketplace
- 跨设备同步
- 完整 evolution 审批流
- 企业级管理 UI (权限管理 / 审计日志 / 团队功能)
- ACP 外部 harness (Codex / Claude Code) 集成
```

**A + B 都要 → MVP 时间表会比单选拉长，但产品差异化更立体。**
关键：群聊的"上帝模式 + 进化"是技术差异化，但 UI 要克制——不暴露技术细节给用户。

---

## 5.4 数据模型 + Memory 架构 (第 4 轮草案 — 待确认)

### 5.4.1 Memory 五层架构

| 层 | 内容 | 谁管 |
|---|---|---|
| 1. Agent 工作记忆 | 当前 session 对话 / workspace | ✅ OpenClaw 自带 (per-agent) |
| 2. 跨 session 持久 | 上次聊过什么 / 记得我是谁 | ✅ OpenClaw `MEMORY.md` + `memory/YYYY-MM-DD.md` + transcripts |
| 3. 跨 persona 知识 | "用户讨厌感叹号" 共享 | ❌ DB.user_facts |
| 4. 房间消息归档 | canonical log | ❌ DB.messages |
| 5. Main Agent 状态 | 路由 / 调度 / evolution | ❌ DB.main_agent_state + audit_events |

**判断：不修改 OpenClaw，DB 在它之外做"系统记忆"层。**
- DB = source of truth
- OpenClaw session = 派生状态（崩了可从 DB 重建：拉 history、塞 ContextPack、调 agent run）
- 数据流：用户消息 → 后端写 DB → 后端通过 SDK 调 target agent → agent 回复 → 后端写 DB → 推 UI
- **单聊不走 Main Agent**，后端直接路由到 sarah/alex/kai
- **Main Agent 只在 3 个时机启动**：群聊调度、需要 LLM 决策时、后台 reflector

### 5.4.2 群聊三模式 (对齐 Google ADK)

| 模式 | 用途 | 触发 |
|---|---|---|
| Sequential | 上游 → 下游 (写 → 审 → 修) | 任务有依赖链 |
| Parallel | 多任务同时跑后合并 | 任务独立可分摊 |
| Loop | 反复改进直到 critic 满意 | 质量收敛型 |

**三个 ADK 坑 + 我们的规避**：

| ADK 坑 | Schema 层规避 |
|---|---|
| output_key 静默为空 | `messages.produced_output_key` + orchestration 校验下游引用必命中 |
| Loop 退出靠 escalate=True | critic 回复 meta 含 `verdict='approved'`；max_rounds 兜底 |
| Parallel output_key 冲突 | `(parallel_group_id, produced_output_key)` 联合唯一索引 |

### 5.4.3 SQLite Schema (主要表 — 第 9 轮简化)

完整 DDL 见 `schema.sql` (待生成)。核心表：

```
users
agent_profiles          -- 指向 personas/<id>/ 目录，DB 是索引；文件是源
                        -- 不再需要 agent_instances 表
rooms / room_members / messages
room_orchestration      -- 群聊调度状态
runs / artifacts        -- runs.kind 含 dm_turn / group_round / review / worker / reflection
context_pack_snapshots  -- 持久化 ContextPack 用于审计 (CodeX/GPT 共识)
permission_grants       -- 权限授予 (CodeX/GPT 共识)
audit_events            -- 右侧 ... 面板的事件源 (CodeX/GPT 共识)
user_facts / user_fact_tags  -- 跨 persona 共享知识 + 标签关联表
main_agent_state        -- main agent kv store
```

**关键设计 (本轮变更)**：
- 🆕 **删除 `agent_instances` 表**：OpenClaw configured agent 本身就是长期实例，DB 不用再建 instance 行
- 🆕 `agent_profiles` 只是 DB 索引，对应 `personas/<id>/` 目录里的 SOUL.md / AGENTS.md / IDENTITY.md / USER.md / TOOLS.md (无 manifest.yaml，运行时参数由 `openclaw.json` agents.list[] 管)
- 🆕 删除 `manifest_version_at_spawn`：不再有 spawn 概念
- 🆕 新增 `context_pack_snapshots` 表（采纳 GPT/CodeX）：存每次 ContextPack 用于审计
- 🆕 新增 `permission_grants` 表（采纳 GPT/CodeX）：权限模型 §5.47
- 🆕 新增 `audit_events` 表（采纳 GPT/CodeX）：右侧 ... 面板事件源
- 保留：`messages.parallel_group_id + produced_output_key` 联合唯一索引防 ADK Parallel 坑
- 保留：`user_facts.superseded_by` 链式覆盖
- 保留：Evolution 只用 `personas/<id>/evolution.md`，不建 DB 表

**agent_profiles 字段**:
```
id                   TEXT PRIMARY KEY    -- "sarah-writer" / "alex-pm" / "kai-engineer" / "main"
runtime_agent_id     TEXT NOT NULL UNIQUE -- 对应 openclaw.json agents.list[].id ("sarah"/"alex"/"kai"/"main")
display_name         TEXT                -- "Sarah" / "Alex" / "Kai"
emoji                TEXT
role_category        TEXT                -- "writer" / "pm" / "engineer" / "main"
workspace_dir        TEXT                -- 相对路径 "personas/sarah-writer"
is_visible           BOOLEAN             -- false for "main"
roles                JSON                -- ["normal", "sequential", "critic", "merger"]
created_at / updated_at
```

OpenClaw 那边在 `openclaw.json` 的 `agents.list[]` 配 model / skills / tools / sandbox 等运行时参数。**两边各管一摊，DB 不重复存运行时配置**。

### 5.4.4 性能与扩展约束

**DB 不是瓶颈**，LLM 调用才是 (DB ~1-20ms vs LLM ~500-5000ms)。但有几条铁律避免后期翻车：

1. **强制 WAL 模式**: `PRAGMA journal_mode=WAL` 启动时设，允许并发读写
2. **禁止 `SELECT *` without LIMIT**: messages 表会涨，必须分页
3. **JSON 列只存不查**: 凡是要按 key 过滤的 (tags / output_keys 等)，拆关联表
4. **ContextPack 上限**: 默认最近 N=30-50 条 messages + 相关 user_facts，phase 2 调优
5. **每周自动 VACUUM + WAL checkpoint**: 防文件膨胀

**多轮对话量级预估** (单用户本地):
- 单聊 50 轮 ≈ 100 条 messages，总 DB 操作 <100ms
- 群聊 Loop 5 轮 × 3 persona ≈ 15 条 messages，DB <50ms
- 真实延迟 99% 在等 LLM

**Main Agent 选模型建议**：调度任务用快模型 (Haiku / Gemini Flash)，subagent 用主力模型。

---

## 5.4.5 OpenClaw 集成策略 (第 8-9 轮)

### 5.4.5.1 不 fork — 当本地 Gateway daemon 用
**核心发现**：OpenClaw 是 Gateway daemon 架构，本来就是给外部应用接的。它"重"是因为 npm 包带了所有可选 channels，**运行时不启用 = 完全不加载**，无成本。

### 5.4.5.2 ⭐ 用 OpenClaw native multi-agent 模式（第 9 轮替换）

```
我们前端 ↔ 我们后端 (SQLite + Orchestrator + @openclaw/sdk)
                ↕
        OpenClaw Gateway (ws://127.0.0.1:18789)
        ├── agents.list[]:
        │   ├── "main"   ← 隐藏调度者
        │   ├── "sarah"  ← visible: 写文案
        │   ├── "alex"   ← visible: PM
        │   └── "kai"    ← visible: 工程师
        ├── tools.agentToAgent = enabled
        └── channels = {} (全关)
```

- OpenClaw daemon: 本地运行，只启 LLM provider extensions，所有 channels 关闭
- 后端调度：直接 SDK 调 `oc.agents.get(id).run(...)`；按需调用 Main agent 做 LLM 决策
- 状态隔离: OpenClaw 在 `~/.openclaw/`，persona workspace 在项目内 `personas/<id>/`，我们 DB 在项目内

### 5.4.5.3 我们设计 vs OpenClaw 原语对齐（更新）

| 我们概念 | OpenClaw 原语 |
|---|---|
| Visible SubAgent (sarah/alex/kai) | `agents.list[]` 各一项 |
| Main Agent | `agents.list[]` id="main"（隐身） |
| Worker Run | `sessions_spawn` raw sub-agent |
| Main → SubAgent 通信 | `tools.agentToAgent` 或 后端 SDK 直调 |
| Persona 人格文件 | OpenClaw 原生 SOUL.md / AGENTS.md / USER.md / IDENTITY.md / TOOLS.md |
| Skills | OpenClaw 原生 SKILL.md (workspace/skills/) |
| Memory 层 1-2 | OpenClaw 自带 |
| 跨 persona 知识 / 房间 / orchestration | 我们 DB + 后端 |

### 5.4.5.4 集成路径（第 10 轮决策完成）

**Q2 闭合**：SDK 支持按 `agentId` 直接触发 normal session run，**不依赖 channel binding**。详见 `openclaw_research.md §4.5 / §4.6 / §15 已闭合`。

**双轨决策**：

| 阶段 | 路径 | 理由 |
|---|---|---|
| **PoC + MVP** | ⭐ **Path C** — OpenAI-compat HTTP `/v1/chat/completions` + `model: "openclaw/<agentId>"` | 用标准 `openai` npm 包即可；workspace 文件、SOUL.md 注入与 SDK 路径同 codepath；最少代码量；不依赖私有包 |
| **Phase 2** | **Path A** — clone openclaw 仓库 + pnpm workspace + `"@openclaw/sdk": "file:../openclaw/packages/sdk"` | 需要 `oc.tools.invoke` / `oc.artifacts` / `oc.approvals` / per-run events 流式 / `agentToAgent` 显式调度时切换 |

**已排除 Path B (Direct WS)**：自己实现 handshake/heartbeat/reconnect/seq gap 维护成本 ~1000+ 行，不值得。

**调用约定（Path C，第 10 轮实证通过）**：
- 后端 → Gateway：`POST http://127.0.0.1:18789/v1/chat/completions`，`Authorization: Bearer <gateway-token>`
- 选 agent：body 写 `"model": "openclaw/sarah"` 或 header `x-openclaw-agent-id: sarah`
- Session 隔离（实证）：
  - **首选**：body 加 OpenAI `user` 字段（如 `"user": "dm:user-1:sarah"`）→ Gateway 自动派生稳定 sessionKey，同一 user 的连续请求落同一 session
  - **显式控制**：header `x-openclaw-session-key: room:42:sarah` 完全自定义路由
  - **默认不传**：端点 stateless per-request，每次新 session（不推荐用于聊天）
- 安全：端点只 loopback，**绝不对外暴露**；Gateway token 走 env，不进 git；OpenAI-compat endpoint 是 owner-trust 级别，任何持 token 的进程都拥有 operator 权限
- 限制：MVP 阶段不用 `tools.invoke` / `artifacts` / `approvals` 这些 Path A 才有的 surface，相应功能要么走 OpenClaw 内部 tools、要么我们后端自管

---

## 5.45 群聊调度策略 (第 7 轮)

### 5.45.1 用"房间类型"包装模式 (隐藏技术词汇)

用户在 UI 上看到的是 3 种**房间类型**，而不是 "Sequential/Parallel/Loop"。

| 内部 mode | UI 房间类型 (MVP 暂定) | 用途 |
|---|---|---|
| sequential | **接龙房** | 一个干完下一个干 (写→审→改) |
| parallel | **头脑风暴房** | 同时上，最后合并 |
| loop | **打磨房** | 反复改到达标 |

(命名 MVP 阶段可改，跑通用户反馈再迭代)

### 5.45.2 Main Agent "不露面"的正确实现

**关键 reframe**：Main Agent 不是"被禁止发言"，是**走另一条数据通道**。

- UI 渲染规则：只显示 `messages.sender_type='agent_instance'` 的消息
- Main Agent 输出 → JSON 结构化决策 → 写入 `main_agent_state` / 调度指令 / 日志
- **不进 messages 表**，自然不在 UI 出现
- 后台可以随时查 Main Agent 日志做 debug

类比：舞台导演不上台，但全程在指挥；观众只看演员。

### 5.45.3 Main Agent 用 LLM 的 5 个场景

| 场景 | 输入 | 输出 |
|---|---|---|
| Parallel 拆指令 | room.goal | 各 persona 的子任务 |
| Parallel 合并 / 召唤 Merger | 各 persona 产出 | 合并报告或选 Merger |
| Loop 收敛判断 | 近 N 轮 verdict + 产出 | continue / converge / escalate |
| 跑偏检测 | subagent 产出 | retry / skip / abort |
| 召唤"出面者" | 已收齐信息但 Main 自己不能露面 | 选定某 persona + ContextPack |

**确定性场景不调 LLM**：
- Sequential 选下一发言者 (按 participant_order)
- Loop 解析 verdict (结构化字段读取)
- ContextPack 模板拼装

### 5.45.4 谁出面对用户汇报最终结果

| 房间类型 | 自然汇报者 |
|---|---|
| 接龙房 (sequential) | 链上最后一位 (顺理成章) |
| 头脑风暴房 (parallel) | **Merger persona** (创建房间时强制选) |
| 打磨房 (loop) | producer 的最后一稿 |

### 5.45.5 Verdict 机制 (Loop 退出)

Critic persona 在回复末尾必须有结构化标记：

```
...(critique content)...

VERDICT: approved | revise | escalate
```

后端正则提取填入 `messages.verdict`。失败兜底走 Main Agent LLM 解析。
ADK 的 `escalate=True` 在我们这里 = `verdict='escalate'` → 上抛给用户决策。

### 5.45.6 ContextPack 格式 (Main Agent 喂给 subagent)

```yaml
room_goal: <房间目标>
your_role: writer | critic | merger | normal
your_task_this_round: <这一轮要干嘛>
inputs:                    # 上游产物，已命名
  <output_key>: <content>
expected_output_key: <你这轮的产出命名>
verdict_required: true|false
constraints: [...]         # 房间或 persona 级硬约束
relevant_user_facts: [...] # 从 DB.user_facts 挑相关的
```

**关键**：ContextPack 由**后端 Orchestrator** 拼好（§1.2 路径 a），不让 subagent 自己读群历史。需要 LLM 决策的部分（拆指令 / 合并 / verdict 解析）通过 SDK 调 main agent，但 pack 模板拼装本身是 Node 代码 + DB 查询，零 LLM 调用。

### 5.45.7 Persona roles 字段 (放 DB.agent_profiles.roles)

```
roles: ["normal", "sequential", "critic", "merger"]
  normal       # 单聊默认
  sequential   # 可在接龙房任意位置
  critic       # 可在打磨房当 critic
  merger       # 可在头脑风暴房当 Merger
```

MVP 三个 persona 全部标全 roles，留口子；实际由房间创建时挑选。
**注**：第 9 轮重构后不再走 `manifest.yaml`，roles 直接进 DB.agent_profiles 表。

### 5.45.8 ContextPack Snapshot 持久化 (采纳 GPT/CodeX)

ContextPack 不只是临时拼装，**每次拼好都要存进 DB**用于审计：

```
context_pack_snapshots (
  id              TEXT PRIMARY KEY,
  target_agent_id TEXT,
  conversation_id TEXT,
  run_id          TEXT,
  purpose         TEXT,         -- dm_turn / group_round / review / worker / reflection
  pack_json       TEXT,         -- 完整 ContextPack 内容
  redactions      JSON,         -- [{source_type, reason, summary_for_audit}, ...]
  created_at      DATETIME
)
```

`redactions[]` 关键字段 (打开 audit 时让用户看到"什么没传给某 agent + 为什么")：

```json
{
  "source_type": "dm | room | artifact | memory",
  "reason": "private | not_relevant | permission_denied | too_large",
  "summary_for_audit": "未把你和 Iris 的私聊传给 Bram (privacy)"
}
```

---

## 5.46 Audit Panel (右侧 ... 面板, 采纳 GPT/CodeX)

UI 默认隐藏，用户点 `...` 展开。目的：让用户**信任**系统（能看到 main agent 做了什么），但不污染主聊天。

### 5.46.1 展示内容

- **Route Decision**：为什么选 Sarah/Alex/Kai；为什么没选某个
- **Context Pack**：给每个 agent 的摘要 + redactions (从 `context_pack_snapshots` 取)
- **Runs**：DM turn / group round / review / worker run
- **Tool Calls**：工具名 / 参数摘要 / 结果摘要 / 是否经审批
- **Permission Events**：谁请求 / 范围 / 用户决定
- **Artifacts**：输出 file / summary / review / diff
- **Cost / Latency**：每个 run 的 token / 耗时
- **Errors / Retries**：失败、重试、降级

### 5.46.2 禁止展示

- 模型完整 chain-of-thought
- 系统 prompt 全文
- 凭证 / token 明文
- 未授权私聊原文
- 安全策略绕过细节

### 5.46.3 数据源

新增 `audit_events` 表：

```
audit_events (
  id              TEXT PRIMARY KEY,
  run_id          TEXT,
  conversation_id TEXT,
  event_type      TEXT,         -- route / context_pack / tool_call / permission / worker_spawn / artifact_created / error / evolution_patch
  public_summary  TEXT,
  redacted_payload_ref TEXT,    -- 指向 artifacts / context_pack_snapshots / runs 等
  created_at      DATETIME
)
```

---

## 5.47 Permission Gateway (采纳 GPT/CodeX)

OpenClaw 官方 docs/gateway/security 明说：它假设的是 **personal assistant trust model**，不是多用户互不信任的边界。所以我们要在产品层加自己的 Permission Gateway。

### 5.47.1 三级风险

| 等级 | 例子 | 处理 |
|---|---|---|
| **low** | 读 room public 消息 / 写普通 memory note / 生成 summary | 自动 |
| **medium** | 读项目文件 / 调 web/search / 修改 SOUL.md 草案 / 把私聊摘要分享进 room | ask 用户 |
| **high** | 写文件 / exec shell / 访问 credential / 改 permission 策略 / 改 OpenClaw config | **必须**审批 |

### 5.47.2 Permission Prompt UI 格式

```
Sarah 想做：读取 ~/Documents/notes.md
范围：仅这个文件，只读
原因：写 Q4 营销总结需要参考你的会议记录
风险：中
有效期：本次 run

[允许一次]  [允许本房间]  [拒绝]
```

### 5.47.3 数据库表

```
permission_grants (
  id                  TEXT PRIMARY KEY,
  user_id             TEXT,
  agent_id            TEXT,
  conversation_id     TEXT,        -- 可空，作用域 room 级时填
  run_id              TEXT,        -- 可空，作用域 run 级时填
  scope               TEXT,        -- read_file / write_file / exec_shell / web / credential / share_private_context / modify_agent_config
  resource            TEXT,        -- 路径 / URL / agent_id ...
  decision            TEXT,        -- allow_once / allow_room / allow_session / deny
  expires_at          DATETIME,    -- 可空
  created_at          DATETIME
)
```

### 5.47.4 流程

```
Tool Call 触发 → Permission Gateway 检查
  ↓ low                        ↓ medium                 ↓ high
执行 + 写 audit_event       查 grant 表        查 grant 表 (即使有也再问)
                            缺则弹 prompt        必弹 prompt
                            用户决 → 写 grant   用户决 → 写 grant
```

### 5.47.5 默认安全策略 (MVP)

```
DM privacy:               strict (Main agent 不读其他 DM)
shell exec:               ask + sandbox required
file write:               ask
credential access:        ask
private context sharing:  ask
agent config mutation:    approval required
worker timeout:           required
max group rounds:         2
```

---

## 5.5 Persona 模版结构 (第 9 轮重写 — 对齐 OpenClaw 原生 workspace)

### 5.5.1 目录结构 (改用 OpenClaw workspace 布局)

```
project-root/
├── personas/                              # 每个目录是一个 OpenClaw agent workspace
│   ├── main/                              # 隐藏 Main Agent
│   │   ├── SOUL.md                        # 编排者人格 (normal session 加载)
│   │   ├── AGENTS.md                      # 编排职责 + 协作规则 (normal + worker 加载)
│   │   ├── TOOLS.md                       # 工具使用习惯
│   │   ├── IDENTITY.md                    # 名字 (虽然不露面，OpenClaw 要求)
│   │   ├── USER.md                        # 用户是谁
│   │   ├── evolution.md                   # ⭐ 产品层 changelog，不进 OpenClaw workspace prompt
│   │   ├── memory/                        # OpenClaw 自管
│   │   └── skills/                        # workspace-local skills
│   ├── sarah-writer/                      # 写文案 persona
│   ├── alex-pm/                           # PM persona
│   └── kai-engineer/                      # 工程师 persona
├── system/                                # 我们项目自己的资产 (不进 OpenClaw)
│   ├── skills-shared/<skill>/SKILL.md     # 跨 persona 共享 skill (可被复制到各 workspace)
│   └── templates/                         # ContextPack 模板等
└── openclaw.json                          # OpenClaw Gateway 主配置 (含 agents.list[])
```

### 5.5.2 Persona 最小文件清单 (OpenClaw 原生)

| 文件 | 必需? | normal session 加载 | worker run 加载 |
|---|:---:|:---:|:---:|
| `SOUL.md` | ✅ | ✅ | ❌ |
| `AGENTS.md` | ✅ | ✅ | ✅ ⭐ |
| `TOOLS.md` | ✅ | ✅ | ✅ ⭐ |
| `IDENTITY.md` | 推荐 | ✅ | ❌ |
| `USER.md` | 推荐 | ✅ | ❌ |
| `evolution.md` | 推荐 | ❌ (产品层) | ❌ |
| `MEMORY.md` | 可选 | ✅ 条件 | ❌ |
| `memory/YYYY-MM-DD.md` | 自动 | 按需 | ❌ |
| `skills/<name>/SKILL.md` | 可选 | 按需 | 按需 |

⭐ AGENTS.md / TOOLS.md 必须含"人格摘要兜底"，因为 Worker Run 看不到 SOUL.md。

### 5.5.3 manifest.yaml 何去何从？

**MVP 删除 `manifest.yaml`**。OpenClaw 原生用 `openclaw.json` 的 `agents.list[]` 配 model / skills / tools / sandbox（第 10 轮实证 schema）：

```json5
{
  models: {
    providers: {
      ruidong: {
        baseUrl: "https://iruidong.com/v1",
        apiKey: "${RUIDONG_API_KEY}",   // 或本地 PoC 内联
        api: "openai-completions",
        models: [
          { id: "ruidong-std", contextWindow: 200000, maxTokens: 98304 },
          { id: "ruidong-plus", contextWindow: 128000, maxTokens: 16384 },
        ],
      },
    },
  },
  agents: {
    defaults: { model: { primary: "ruidong/ruidong-std" } },
    list: [
      {
        id: "sarah",
        workspace: "/abs/path/to/personas/sarah-writer",
        model: { primary: "ruidong/ruidong-std" },
        // skills / tools.deny / sandbox 等按需加
      },
      { id: "alex", workspace: "..." },
      { id: "kai",  workspace: "..." },
    ],
  },
}
```

⚠ **OpenClaw `agents.list[].id` 不带 `-writer` 后缀**：实证里我们用 `sarah`/`alex`/`kai`（产品层 DB 里的 `agent_profiles.id` 可以保留 `sarah-writer` 这类长名作为索引，但 OpenClaw 那边短 id 更顺手）。两层 id 之间在 DB 字段 `workspace_dir`/`runtime_agent_id` 之间映射即可。

我们 DB `agent_profiles` 表只存产品层信息：
- `display_name` / `emoji`
- `role_category` (writer / pm / engineer / main)
- `is_visible` (true for sarah/alex/kai, false for main)
- `roles` (normal/sequential/critic/merger — 群聊角色)
- `workspace_dir` (指向 `personas/<id>/`)

**两边各管一摊，不重复**。

### 5.5.4 Skills 设计原则 (更新)
- **OpenClaw 原生格式**：每个 skill 一个 `SKILL.md`，frontmatter + markdown body
- **每个 persona workspace 自己的 `skills/` 目录**：最高优先级
- **跨 persona 共享**：通过 `~/.openclaw/skills/` 或 `system/skills-shared/` 维护一份源，**启动时拷贝**到各 persona workspace 的 skills/；或用 OpenClaw 的 `skills.load.extraDirs` 配置
- 加 skill = 写文件 + restart Gateway
- **Persona 私有 skill**：直接放 `personas/<id>/skills/<skill-name>/SKILL.md`

### 5.5.5 Evolution.md 格式 (append-only changelog) — 加 Quality Signal 字段

```markdown
## 2026-06-15 14:32 [applied]
**Proposed by:** reflector
**Target file:** SOUL.md
**Quality Signal:** user_correction_repeated x12  (refer to audit_event:abc-123)
**Reason:** 用户在 12 次对话中明确改写 Sarah 输出，去除感叹号
**Evidence:**
  - message:m_001 / m_034 / m_178 (用户改写)
  - artifact:a_009 (用户最终版)
**Patch:**
  + 写作风格：避免感叹号
**Risk:** low
**Rollback:** 删除新增一行
**Status:** applied
```

- Status: `applied` / `pending-review` / `rejected` / `rolled-back`
- 审批 gate: MVP 全人审；后期可配置（low risk 自动 / medium 人审 / high 必审）
- Quality Signals (来源信号枚举，采纳 GPT 建议):
  - `user_thumbs_down` / `user_correction_repeated` / `user_rewrite`
  - `tool_failure` / `permission_denied` / `timeout`
  - `agent_uncertainty` / `repeat_advice` / `cross_agent_disagreement`
  - `review_artifact_rejected` / `user_left_room`
- 信号写进 `audit_events` 表，evolution.md 引用 audit_event id

### 5.5.5a EvolutionPatch DB 表 — MVP 不做，Phase 2 候选

如果将来要走"low risk 自动 apply / medium 人审/灰度 / high 必审 + rollback"完整流程，需要 DB 表：

```
evolution_patches (
  id, target_agent_id, patch_type, proposed_diff, reason, evidence_refs,
  risk_level, approval_status, applied_at, rolled_back_at, rollback_plan
)
```

MVP 阶段 markdown changelog 足够。

### 5.5.6 三个首发 persona 的 skills 草案

**Sarah (写文案)** 
- `anti-ai-tone` ⭐ — 去 AI 味道 (避免赋能/打造/不仅而且/分点症)
- `red-book-style` / `wechat-article-style` / `weibo-style`
- `email-tone-adapter`
- MCP: filesystem / notion

**Alex (PM)** 
- `user-story-decomposer` (INVEST)
- `prd-skeleton`
- `priority-frameworks` (RICE/MoSCoW/Kano)
- `competitor-research-frame`
- MCP: filesystem / notion

**Kai (工程师)** 
- `code-review-checklist`
- `systematic-debug`
- `architecture-tradeoff`
- `tdd-discipline`
- MCP: filesystem / git / shell (受限)

### 5.5.7 关键判断
- **anti-ai-tone 是产品差异化的杀手 skill**：可做成系统级，任何 persona 调用
- **模版可扩展**通过 4 个维度满足：加 persona / 加 skill / 加 MCP / 改 soul，都不改架构
- **进化能力限定为"改文本"**：MVP 阶段 reflector 只能改 `personas/<id>/` 下的 markdown 文件（SOUL/AGENTS/USER/IDENTITY/TOOLS）+ (后期) 新增 SKILL.md；改 `openclaw.json` runtime 参数（model/skills/tools.deny）属于 high-risk，必须 §5.47 Permission Gateway 显式审批；不让它写可执行代码

---

## 6. 下一轮入口（任选）

已完成（第 10 轮）：
- ~~B. 第一个 persona workspace~~ ✅ `personas/sarah-writer/` 全 5 文件落地
- ~~C. 最小 `openclaw.json`~~ ✅ 含 ruidong provider + 2 agents，doctor 通过
- ~~D. PoC 端到端~~ ✅ `verify-openclaw.mjs` 3/3 行为 case 通过
- ~~E. 验证 SDK 直调能力~~ ✅ Q2 闭合（`openclaw_research.md §4.5 / §15`）
- ~~F. 完整复检 doc~~ ✅ 第 11 轮（本轮）

仍开放（第 13 轮刷新）：
- ~~G. 多 agent 共存验证~~ ✅ 完成（第 12 轮）
- ~~J. memory_search 接 embedding~~ ✅ 完成（第 13 轮）— bge-m3 接 `openai-compatible` provider 跑通；端到端 sarah 召回 + 引用 source ref
- **A. 写 schema.sql**：把第 9 轮简化后的 schema 落地成可执行 DDL（含 audit_events / permission_grants / context_pack_snapshots 等新表）
- **H. 后端骨架**：起 Express/Hono，把 telegram-style chat UI 跟 Gateway 桥起来（DM 直路由 first）
- **I. anti-ai-tone 杀手 skill**：写 `system/skills-shared/anti-ai-tone/SKILL.md`，验证 skill 注入是否真的让 Sarah 输出更"不像 AI"
- **K. memory 写入触发器**：实证发现 model 不会自动写 memory；要么人工编辑 `personas/<id>/memory/YYYY-MM-DD.md` + `openclaw memory index --force`，要么后端做 reflector loop 提取用户偏好定期写入（与第 9 轮 §2.5 进化机制合并）
- **L. agents.defaults.tools.profile 调整**：现在用的是 onboard 默认 "coding" profile，过滤了 5 个工具（agents_list, gateway, message, nodes, tts）；非 coding agent (sarah/alex) 可能要换 profile 或 per-agent tools 配置

**倾向 H → A**：先起后端拿 UI 跑起来（用户能真正"打开 Sarah/Alex/Kai 聊"），schema 配着 UI 需要的字段一起写。I/K/L 作为 Phase 1.5 候选。

---

## 已评估并放弃 (第 9 轮，CodeX docs 评审后记录)

避免下一轮讨论再绕回来：

- **AgentRuntimeAdapter interface**：YAGNI。MVP 单 runtime；用 `runtime/openclaw.ts` thin client 替代抽象层
- **`runtimeType` 字段进 schema**：单 runtime，过早泛化
- **Bram/Luna/Echo/Iris/Atlas catalog**：那是内部工具团队 vibe，我们职业向 (Sarah/Alex/Kai) 不动
- **SOUL/AGENTS/TOOLS/MEMORY 四文件全列为产品主权**：错。OpenClaw 原生 workspace 文件由 `agents.list[]` materialize；我们 DB 只存索引
- **EvolutionPatch DB 表 (MVP)**：markdown changelog 够；Phase 2 走自动 apply 时再开 (§5.5.5a 已留口子)
- **Chat / Convene / Review 顶部 tab 状态**：保留按钮作为动作入口，但底层不做 tab state，仍按 room type 决定模式

---

## 修订记录

- 2026-05-29 第 1 轮：建立基础架构 + OpenClaw 约束侦察。
- 2026-05-29 第 2 轮：产品定位澄清 (Telegram=UI 风格，本地 Web 单用户 MVP，职业向 persona)。Channel 问题关闭。新增护城河 A/B 选择 + persona 模型重新框定。
- 2026-05-29 第 3 轮：护城河选 A+B (拖慢但差异化更立体)。首发 persona 定为 写文案/PM/工程师。新增设计哲学：UI 轻 + 能力深 (Skills/MCP)，SubAgent 模版必须可扩展。MVP 排除企业级管理 UI。
- 2026-05-29 第 4 轮：Persona 模版结构成型 (soul.md + manifest.yaml + evolution.md + skills/)。Skills 用 OpenClaw 原生 SKILL.md 格式。系统池 + persona 白名单设计。Model 走 OpenRouter 聚合。MVP 不做"Main Agent 生成可执行代码"，进化能力限定为"改文本"。三个 persona 的 skills 草案落地。
- 2026-05-29 第 5 轮：Memory 五层架构定型 (OpenClaw 管 1-2 层，DB 管 3-5 层)，不修改 OpenClaw。数据流：DB 是 source of truth，subagent session 是派生态。单聊不走 Main Agent。群聊对齐 ADK 三模式 + schema 规避三个坑。SQLite 数据模型成型。
- 2026-05-29 第 6 轮：Evolution 不建 DB 表，evolution.md 单一来源。Schema 性能加固：WAL 模式 / tags 拆关联表 / 强制分页 / 每 profile 单 active instance / 定期 VACUUM。Main Agent 调度建议用快模型。
- 2026-05-29 第 7 轮：群聊调度策略成型。三种房间类型 (接龙房/头脑风暴房/打磨房) 替代技术词暴露。Main Agent "不露面" 重新定义为"走另一条数据通道，不进 messages 表"，不是禁止发言。明确 5 个 LLM 场景 + 4 个确定性场景。Parallel 房强制选 Merger。Verdict 走结构化标记 + 正则提取。Persona manifest 增 roles 字段。
- 2026-05-29 第 8 轮：OpenClaw 集成策略定型。**不 fork，不剥离**，当本地 Gateway daemon 用 (`ws://127.0.0.1:18789`)。仅启 LLM provider，全关 channels，不装 apps。我们设计与 OpenClaw 原语几乎 1:1 对齐 (SOUL.md / SKILL.md / sessions_spawn / resume)。文件名 `soul.md` → `SOUL.md` 对齐原生。集成路径倾向 `@openclaw/sdk`，待验证私有包安装可行性。
- 2026-05-30 第 9 轮：⭐ **重大架构修订**。深度查 OpenClaw docs 发现原生 `agents.list[]` 多 per-persona configured agent 模式，第 1-8 轮的"Main spawn visible SubAgent (raw sub-agent)"模型推翻。Visible SubAgent (sarah/alex/kai) 现在各是 OpenClaw configured agent；Worker Run 才走 `sessions_spawn`。"重生模式" / `resumeSessionId only-spawner` / `manifest_version_at_spawn` 等设计**全部删除**。Persona 模版从 `manifest.yaml + soul.md` 改为 OpenClaw 原生 workspace 文件 (SOUL/AGENTS/USER/IDENTITY/TOOLS)；运行时参数 (model/skills/tools/sandbox) 进 `openclaw.json` 的 `agents.list[]`，DB `agent_profiles` 只留产品层索引。CodeX docs 评审：采纳 Audit Panel (§5.46) / Permission Gateway (§5.47) / ContextPack Snapshot 持久化 (§5.45.8) / 6 状态 / Worker Run 一等公民 / Quality Signals (§5.5.5)；拒绝 AgentRuntimeAdapter / runtimeType / Bram-Luna catalog / EvolutionPatch DB 表。CodeX 关于 AGENTS.md/TOOLS.md 是 OpenClaw 原生的判断 ✅ 修正；Worker Run 只加载 AGENTS.md+TOOLS.md (官方文档证实，§3 硬约束)。下一步 E → C → D。
- 2026-05-30 第 10 轮：**实证完成**。SDK Q2 闭合：`Agent.run({agentId})` 支持按 agentId 直接触发 normal session run (`openclaw_research.md §4.5`)。集成路径双轨决策：**PoC + MVP 走 Path C (OpenAI HTTP `/v1/chat/completions` + `model: "openclaw/<id>"`)**，Phase 2 才切 Path A (workspace + file: SDK)。落地 `openclaw.json` + `personas/sarah-writer/` 全 5 文件 + `personas/main/` stub。接入 ruidong provider (OpenAI-compat, `baseUrl=https://iruidong.com/v1`, ruidong-std → glm-5.1 后端适合中文写作)。修复 `~/.openclaw/` root ownership 问题（sudo chown）；`openclaw gateway install`+`start` 跑起 LaunchAgent；`/v1/models` 列出 `openclaw/sarah` 验通过。`verify-openclaw.mjs` 端到端 3/3 行为 case 通过（identity / unknown-info-honesty / ask-first-when-ambiguous）；style case 行为正确但 regex 字面包含检查误判。写两个验证脚本：`test-ruidong-direct.mjs`（绕过 Gateway 直测 prompt 工程，快 10×）+ `verify-openclaw.mjs`（端到端 Path C 验证）。
- 2026-05-30 第 11 轮：**doc 复检**。修订 9 处第 9-10 轮没改干净的地方：顶部状态标注；§1 架构图 SDK→Path C；§4.1 模型选项对齐 ruidong 现实；§5 MVP 删除"按需 spawn"旧概念；§5.4.3 `agent_profiles` 加 `runtime_agent_id` 字段映射；§5.4.5.4 sessionKey 隔离从"待验证"→ 实证结论 (OpenAI `user` 字段派生 / `x-openclaw-session-key` header)；§5.45.6 ContextPack 拼装从"Main Agent"改为"后端 Orchestrator"对齐 §1.2 路径 a；§5.5.3 配置示例 model 切到 `ruidong/ruidong-std` + 增加 `runtime_agent_id` 短/长 id 映射说明；§5.5.7 删 manifest 白名单引用；§6 入口标记完成 + 列下一步 G/H/I。
- 2026-05-30 第 12 轮：**多 agent 共存实证**（任务 G ✅）。落地 `personas/alex-pm/` + `personas/kai-engineer/` 各 5 文件 workspace；扩 `openclaw.json` agents.list 到 4 项（main + sarah/alex/kai），kai 切 ruidong-plus（kimi-for-coding 后端，适合工程任务）。`scripts/verify-multi-agent.mjs` 5/5 case 通过：身份差异化 / 跨 agent session 隔离 / 同 agent 同 user 跨 turn 连续 / 同 agent 不同 user 应独立 / 三视角差异。**关键超预期发现**：alex 主动说出"具体方案留给工程（kai 的事）"——从 SOUL.md 边界条款"不替工程拍技术方案（kai 的事）"直接生效，**跨人格协作认知不需要 main agent 调度，三个 visible agent 自己就知道边界**。**实证发现**：OpenClaw 内置 `memory_search` 工具有 fallback 提示"缺 embedding provider 配置"——ruidong 列了 `bge-m3` 是 embedding，要配进 `openclaw.json` 让长期记忆检索能跑（开任务 J，Phase 1.5 候选）。下一步推荐 H → A。
- 2026-05-30 第 13 轮：**长期记忆 / embedding 跑通**（任务 J ✅）。`openclaw.json` 加 `agents.defaults.memorySearch = {provider: "openai-compatible", model: "bge-m3", remote: {baseUrl: "https://iruidong.com/v1/", apiKey}}`，复用 ruidong endpoint 的 embedding 模型（1024 维）。`openclaw memory status --deep` 显示 4 agent 各自独立 memory store `~/.openclaw/memory/<id>.sqlite`，全部 `Embeddings: ready` / `Vector store: ready`。写 `personas/sarah-writer/memory/2026-05-30.md` 示例 + `openclaw memory index --force` 重建索引；端到端验证：通过 chat 让 sarah 查"App Store 描述长度"——sarah 主动调用 `memory_search` 工具 → 向量检索匹配到 chunk → 给出准确答案 "< 170 字" + source ref `memory/2026-05-30.md#L15`。**关键学习**：model 主动调 `memory_search` 取决于 system prompt 触发，query 用 "查一下记忆 / 你之前记过的" 是更稳的触发；如果 system prompt 已经覆盖问题（如 USER.md 里），model 不会 reach memory 层。openclaw_research.md 新增 §17 完整配置参考。开新任务 K（memory 写入触发器，与 §2.5 进化机制合并）和 L（tools.profile 调整）。
