# TelegramAgent 当前实现快照

> 写于 2026-05-30，更新于 2026-05-31。和 `../CLAUDE.md` 配套——CLAUDE.md 是"项目入口和约定"，本文档是"目前的代码长什么样、跑起来什么样"。
> 历史决策见 `../temp_design.md`；遗留问题见 `../ISSUE.md`。

## 1. 一句话定义

本地单用户的 Telegram 风格 AI 助手 web 应用：用户可以和多个职业 persona（写文案的 Sarah / PM 的 Alex / 工程师的 Kai / 小丸子）单聊，也可以在显式群房里让多个 OpenClaw configured agents 顺序参与。隐藏 Main agent 后续用作群聊编排者 / 后台管理员。基于 OpenClaw runtime。

## 2. 运行时拓扑

```
┌────────────────────────┐
│ 浏览器                  │  React + Vite，http://127.0.0.1:5183
└────────────┬───────────┘
             │  /api/* (Vite proxy)
             ↓
┌────────────────────────┐
│ Backend (Hono)          │  http://127.0.0.1:18791
│  - /api/agents          │
│  - /api/rooms           │
│  - /api/rooms/:id/      │
│      messages (SSE)     │
└────────────┬───────────┘
             │  POST /v1/chat/completions
             │  model: "openclaw/<agentId>"
             │  Bearer <gateway-token>
             │  + injected <env> system block
             ↓
┌────────────────────────┐
│ OpenClaw Gateway        │  http://127.0.0.1:18789
│  agents.list = [        │
│    main, sarah,         │
│    alex, kai, maruko    │
│  ]                      │
│  workspace 见 personas/ │
└────────────┬───────────┘
             │  (provider)
             ↓
┌────────────────────────┐
│ ruidong (OpenAI-compat) │  https://iruidong.com/v1
│  - ruidong-std → glm-5.1│  (sarah / alex / main)
│  - ruidong-plus → kimi  │  (kai)
│  - bge-m3 (embedding)   │  (memory_search)
└────────────────────────┘
```

DM 消息走法：
1. 前端 `POST /api/rooms/sarah/messages { prompt, runId }`
2. 后端写 `messages` 表（sender=human）→ 开 SSE stream
3. 后端调 `streamOpenClaw({ agentId: 'sarah', userText, sessionUser: 'me:sarah' })`
4. OpenClaw 把目标 agent 自己的 SOUL/IDENTITY/USER/AGENTS/TOOLS 拼成 system prompt，调 ruidong
5. ruidong 流式返回 → OpenClaw → 后端 → 翻译成 AgentUX 事件（`run.started` / `text.started` / `text.delta` / `text.finished` / `run.finished`）→ 前端
6. 整段累完后端写 `messages`（sender=agent）

群房 MVP 走法：
1. 前端根据 room / `@mention` / `memberIds` 解析 `agentIds`
2. 后端校验目标 agent 都是 room members
3. 后端按 `agentIds` 顺序串行调用 OpenClaw
4. 每个 agent 使用 `sessionUser = me:<roomId>:<agentId>` 隔离上下文
5. 每个 agent 输出独立写入 `messages`

当前接龙房是 one-shot sequence：一条用户消息触发成员按顺序各说一次，然后停止。Main 的 stop/continue/escalate 判断放 Phase 2。细节见 [`14_AGENT_COMMUNICATION_PROTOCOL.md`](14_AGENT_COMMUNICATION_PROTOCOL.md)。

## 3. 目录布局

```
TelegramAgent/
├── CLAUDE.md                ← 项目入口 + 约定
├── ISSUE.md                 ← 遗留清单
├── temp_design.md           ← 13 轮设计 audit trail
├── openclaw_research.md     ← OpenClaw 调研笔记
├── openclaw.json            ← Gateway 主配置（agents.list / providers）
├── personas/                ← 每个 agent 的 OpenClaw workspace
│   ├── main/                  ← 隐藏 orchestrator (MVP stub)
│   ├── sarah-writer/          ← 写文案
│   ├── alex-pm/               ← PM
│   └── kai-engineer/          ← 工程师
│       └── {IDENTITY,SOUL,USER,AGENTS,TOOLS,HEARTBEAT}.md
├── backend/                 ← Hono + node:sqlite
│   ├── .env
│   ├── data/telegram-agent.sqlite
│   └── src/
│       ├── server.ts          ← Hono app + CORS + route 挂载
│       ├── db.ts              ← 内联 DDL + 查询封装（4 表）
│       ├── agentSync.ts       ← 把 personas/ 同步进 agent_profiles 表
│       ├── envBlock.ts        ← 当前时间 → <env> 注入
│       ├── openclaw.ts        ← streamOpenClaw（Path C）
│       └── routes/
│           ├── agents.ts        ← GET /agents（含 presence）
│           ├── rooms.ts         ← GET /rooms, /rooms/:id/messages
│           └── messages.ts      ← POST /rooms/:id/messages (SSE)
├── frontend/                ← React + Vite
│   ├── vite.config.ts         ← /api → 18791 proxy
│   ├── public/theme-avatars/  ← 4 主题 × 4 角色 PNG
│   └── src/
│       ├── App.tsx              ← 3700 行 monolith（见 ISSUE.md）
│       ├── styles.css
│       ├── agentExpressions.ts  ← 表情 placeholder Chinese 化
│       ├── agentSouls.ts        ← 前端展示用的 persona 卡片
│       └── ...
├── scripts/                 ← 验证 OpenClaw 用的 mjs 脚本
└── docs/                    ← 本目录（本文件 + 旧 GPT 设计 stale）
```

## 4. 数据库 schema（当前）

`backend/src/db.ts` 内联 DDL。4 张表：

```sql
users (id, display_name, created_at)
  -- 单用户：只有一行 'me' / 'Ricky'

agent_profiles (id, name, role, profile, model, hidden, emoji, color, initials, updated_at)
  -- 启动时 agentSync.ts 从 personas/*/IDENTITY.md 解析 upsert
  -- hidden=1 的不在 GET /api/agents 返回

rooms (id, kind, title, agent_id, member_ids JSON, created_at)
  -- kind: 'agent' (DM) | 'room' (group)
  -- DM room.id == agent_id；group room member_ids 是 JSON array

messages (id, room_id, sender, agent_id, body, created_at)
  -- sender: 'human' | 'agent' | 'system'
  -- INDEX (room_id, created_at)
```

更多设计中的表（`runs` / `artifacts` / `audit_events` / `permission_grants` / `context_pack_snapshots` / `user_facts`）见 `../temp_design.md §5.4.3`。当前群聊协议债务见 [`14_AGENT_COMMUNICATION_PROTOCOL.md`](14_AGENT_COMMUNICATION_PROTOCOL.md)。

## 5. 跟 OpenClaw 怎么对话

**Path C**：OpenAI-compat HTTP。

```http
POST http://127.0.0.1:18789/v1/chat/completions
Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>
Content-Type: application/json

{
  "model": "openclaw/sarah",
  "messages": [
    { "role": "system", "content": "<env>\n当前时间: ...\n</env>\n..." },
    { "role": "user", "content": "..." }
  ],
  "stream": true,
  "user": "me:sarah"
}
```

- 不用 `@openclaw/sdk`（Path A 是 Phase 2 候选）
- 不直接连 WebSocket（Path B 已拒绝）
- system 消息我们注入的部分**会被 OpenClaw 接受并和 workspace-derived prompt 拼起来**（实证通过）
- `user` 字段让 Gateway 派生稳定 sessionKey，同 user 跨 turn 复用 session

## 6. AgentUX SSE 事件协议（后端 → 前端）

每条 SSE 消息：

```
event: agentux
data: {"id":"evt_...","runId":"run_...","threadId":"<roomId>","seq":N,"ts":...,"visibility":"user","type":"text.delta","payload":{...},"messageId":"..."}
```

事件类型：
- `run.started` — turn 开始
- `text.started` — 一段文本开始
- `text.delta` — 增量片段
- `text.finished` — 一段文本结束
- `run.finished` — turn 结束
- `run.error` — 出错

前端按 `runId` + `messageId` 把 delta 拼成 bubble。

⚠️ **`runId` 必须前后端对齐**——前端 `nextRunId()` 生成传给后端，后端用同一个。早期版本各自 randomUUID 导致前端拼不出 bubble，已修。

群房 sequential run 里可以出现多个 `text.started` / `text.delta` / `text.finished` 序列。每个文本事件必须携带可解析的 `agentId`，否则前端会把后续 agent 的直播内容错误归到 run 的第一个 agent。

## 7. Persona system prompt 构成

OpenClaw 启动时把**目标 agent 自己** workspace 下的 `*.md` 文件拼成 system prompt（IDENTITY / USER / SOUL / AGENTS / TOOLS / HEARTBEAT），再把 allowlist 内 skill 的 name+description（~100 tokens 一个）progressive-load 进去。然后请求时把 caller 注入的 system 消息接上。

例如调用 `model: "openclaw/sarah"` 时，加载的是 Sarah 自己的 workspace prompt，不会因为 `agents.list[]` 里还有 Alex/Kai/Maruko/Main，就自动把所有 persona 的 `SOUL.md` / `IDENTITY.md` 注入同一次请求。

OpenClaw 的临时 `sessions_spawn` sub-agent 更小：只注入 `AGENTS.md` / `TOOLS.md`，不注入 `SOUL.md` / `IDENTITY.md` / `USER.md`。它适合做 Worker Run，不适合当可见人格容器。

`IDENTITY.md` 是名片（少改），`SOUL.md` 是行为说明书（频繁迭代）。详细分工见 `../CLAUDE.md` "Persona workspace 文件"段。

上下文暴涨的主要风险不在 OpenClaw 默认加载，而在我们自己的编排层：Main/Admin 如果手写所有 persona 全量信息、群聊 ContextPack 塞完整 raw history、evolution loop 默认读全部 DM 原文、或给每个 agent allowlist 过多 skills，都会把上下文撑大。设计上应使用轻量 agent registry 摘要，只有选中候选 agent 后才按需读取详细 persona 文件。

当前 `backend/src/routes/messages.ts` 的 `buildAgentPrompt()` 只是临时 MVP ContextPack：用文本拼接用户请求和前序 agent 输出。最终协议需要结构化 ContextPack、输入粒度规则、redactions 和 context snapshots。详见 [`14_AGENT_COMMUNICATION_PROTOCOL.md`](14_AGENT_COMMUNICATION_PROTOCOL.md)。

**热重载不支持**。改完文件要 `openclaw gateway restart`。

## 7.5 Skills（per-agent allowlist）

每个 persona 由 `~/.openclaw/openclaw.json` 里 `agents.list[].skills: string[]` 显式 allowlist 收窄。当前清单：

| Persona | Skills | 来源 |
|---|---|---|
| main | `dispatching-parallel-agents` | personal `~/.agents/skills/` |
| sarah | `minnow-writing`, `clarity-and-grace` | workspace `personas/sarah-writer/skills/`（ClawHub 装的） |
| alex | `prd`, `project-spec` | personal |
| kai | `systematic-debugging`, `verification-before-completion`, `feature-guardian` | personal |

**机制**：OpenClaw 启动时扫三处 skill 源——bundled (npm package) / personal (`~/.agents/skills/`) / workspace (`personas/<id>/skills/`)，allowlist 按 SKILL.md frontmatter `name` 字段匹配（不是文件夹名）。验证：`openclaw skills list --agent <id>`。

## 8. Presence 模型

`GET /api/agents` 返回 `{ agents, gatewayUp }`。每个 agent 有 `presence` 字段：

| 状态 | UI 颜色 | 触发 |
|---|---|---|
| `online` | 🟢 绿 | Gateway 可达 + 5 分钟内有消息 |
| `idle` | 🟡 黄 | Gateway 可达 + 5 分钟以上没消息 |
| `offline` | ⚫ 灰 | Gateway 不可达 |

Gateway probe 30 秒缓存一次。前端每 30 秒 poll `/api/agents` 刷新。

## 9. 想看更细的设计

- 第 1-13 轮决策链：`../temp_design.md`
- OpenClaw 内部模型 / 配置 schema / Channels：`../openclaw_research.md`
- 群聊通信协议 / 接龙停止规则 / ContextPack 债务：[`14_AGENT_COMMUNICATION_PROTOCOL.md`](14_AGENT_COMMUNICATION_PROTOCOL.md)
- 还没动手的功能（Audit / Permission / Evolution）：`../ISSUE.md` + `../temp_design.md §5.45-§5.47`

## 10. 跟旧 GPT 设计文档（本目录 01-12）的关系

`01_CORE_DECISIONS.md` ~ `12_MVP_PLAN_AND_VALIDATION.md` 是 2026-05-29 GPT 起的早期设计，基于"Main spawn Bram/Nova/Atlas/Iris"模型——第 9 轮被原生 multi-agent 推翻。**已 stale**，保留作历史参考。每个文件顶部有 `[STALE]` banner。
