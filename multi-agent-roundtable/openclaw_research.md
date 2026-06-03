# OpenClaw 调研笔记

> 用途：本项目集成 OpenClaw 的所有事实性发现。设计决策见 `temp_design.md`，这里是**纯客观信息**，便于后续查证。
> 调研日期：2026-05-29 ~ 2026-05-30
> 数据来源：github.com/openclaw/openclaw (main 分支)、官方 docs.openclaw.ai (部分内容通过仓库内 docs/ 目录访问)

---

## 1. 项目本质

OpenClaw 不是单体应用，是**本地 Gateway daemon + 客户端 SDK** 模式：

- **Gateway daemon**: 长期常驻进程，默认监听 `ws://127.0.0.1:18789`
- **外部应用**: 通过 SDK / WebSocket 协议 / HTTP API 调用 Gateway
- **Companion apps** (macOS menu bar / iOS / Android): 全部可选

官方表述："The Gateway alone delivers a great experience. All apps are optional."

启动方式：
```bash
npm install -g openclaw@latest
openclaw onboard --install-daemon       # 装系统级 daemon (launchd / systemd)
# 或 dev: openclaw gateway --port 18789 --verbose
```

状态目录: `~/.openclaw/` (可用 `OPENCLAW_STATE_DIR` 覆盖)

---

## 2. 仓库结构

```
openclaw/                       # 根
├── packages/                   # 公共/SDK 包 (我们关心)
│   ├── agent-core/             # 核心 agent runtime 抽象
│   ├── gateway-client/         # WS 传输客户端
│   ├── gateway-protocol/       # 协议定义
│   ├── sdk/                    # @openclaw/sdk 公开客户端 API
│   ├── plugin-sdk/             # 内嵌插件 SDK (扩展开发用)
│   ├── memory-host-sdk/        # 内存层 SDK
│   ├── net-policy/             # 网络策略
│   ├── plugin-package-contract/
│   └── speech-core/
│
├── apps/                       # 客户端 apps (全部可选)
│   ├── macos/ ios/ android/ macos-mlx-tts/ shared/ swabble/
│
├── extensions/                 # 扩展插件 (按需启用)
│   ├── anthropic/ openai/ openrouter/ deepseek/ ... # LLM providers
│   ├── discord/ telegram/ slack/ whatsapp/ feishu/ wechat/ ... # IM channels
│   ├── browser/ canvas/ codex/ acpx/ mcporter/ ... # 工具/桥接
│   ├── memory-lancedb/ active-memory/ memory-honcho/ ... # 记忆后端
│   └── ...
│
├── skills/                     # 内建 skill 库 (SKILL.md 格式)
│   ├── github/ notion/ obsidian/ apple-notes/ discord/ ...
│
├── src/                        # 核心源代码
│   └── agents/                 # agent runtime 实现
│       ├── acp-spawn.ts        # spawnAcpDirect() 入口
│       ├── subagent-capabilities.ts
│       └── tools/
│           ├── sessions-history-tool.ts
│           ├── sessions-send-tool.ts
│           └── sessions-send-tool.a2a.ts
│
├── docs/                       # 文档源 (Markdown)
│   ├── concepts/
│   │   ├── agent.md soul.md session.md memory.md
│   │   ├── multi-agent.md delegate-architecture.md
│   │   ├── agent-runtimes.md agent-workspace.md
│   │   ├── openclaw-sdk.md
│   │   └── ...
│   └── gateway/
│       ├── protocol.md configuration.md
│       ├── openai-http-api.md tools-invoke-http-api.md
│       └── ...
│
├── openclaw.mjs                # CLI 入口
├── package.json
└── pnpm-workspace.yaml         # monorepo workspace 定义
```

---

## 3. 关键源文件 (Round 1 侦察发现)

| 文件 | 作用 | 关键事实 |
|---|---|---|
| `src/agents/acp-spawn.ts` | **ACP 外部 harness spawn 入口**（Codex / Claude Code / Gemini CLI 通过 ACP 协议接进来） | `spawnAcpDirect()`；参数 `task`/`agentId`/`model`/`runTimeoutSeconds`/`cwd`/`mode`/`sandbox`/`resumeSessionId`。**不是用来 spawn OpenClaw 内部 visible SubAgent**，这是历史上调研踩的坑 |
| `src/agents/tools/sessions-history-tool.ts` | 读取另一 session 历史 | `sessions_history` 工具，可跨 agent 读 (受 access control) |
| `src/agents/tools/sessions-send-tool.ts` | 跨 session 注入消息 | `sessions_send` 工具；单 agent 内多 session 通信 |
| `src/agents/tools/sessions-send-tool.a2a.ts` | A2A ping-pong 流 | `runSessionsSendA2AFlow()` 支持 `maxPingPongTurns` 多轮 |
| `src/agents/subagent-capabilities.ts` | 子 agent 能力管理（仅 sessions_spawn / ACP 场景） | `subagentRole` ∈ {main, orchestrator, leaf}; `subagentControlScope` 当前只有 "children" (无法看到 grandchildren) |
| `src/config/types.agents.ts` | Agent 配置 schema（`agents.list[]`） | `AgentConfig`: id/name/agentDir/workspace/skills/model/tools/permissions/sandbox/groupChat (启动时加载，无 hot-reload) |
| `src/config/zod-schema.agents.ts` | Agent 配置校验 | Zod 解析 |
| `src/config/sessions/` | Session 持久化 | session entry 存储位置，per-agent |
| `src/agents/agent-bundle-mcp-tools.ts` | Tool materialization | session start 时静态加载 manifest |
| (todo) `src/...tools.agentToAgent` | 跨 agent 调用工具 | 第 9 轮发现的关键能力，源文件位置待查 |

---

## 4. SDK API (`@openclaw/sdk`)

来源: `docs/concepts/openclaw-sdk.md`

### 连接

```typescript
import { OpenClaw } from "@openclaw/sdk";

const oc = new OpenClaw({
  url: "ws://127.0.0.1:18789",
  token: process.env.OPENCLAW_GATEWAY_TOKEN,
  requestTimeoutMs: 30_000,
});
await oc.connect();
```

### 核心 Surfaces

| API | 状态 | 用途 |
|---|---|---|
| `oc.agents` | Ready | list/create/update/delete/get agent handles |
| `Agent.run()` | Ready | 启动 agent run，返回 `Run` |
| `oc.runs` | Ready | 管理 run 生命周期 |
| `Run.events()` | Ready | 流式事件 (含 fast-run replay) |
| `Run.wait()` | Ready | 阻塞等待 `RunResult` |
| `Run.cancel()` | Ready | 通过 `sessions.abort` 取消 |
| `oc.sessions` | Ready | create/resolve/send/patch/compact/get |
| `Session.send()` | Ready | 调 `sessions.send`，返回 `Run` |
| `oc.tools` | Ready | 列出/作用域/调用工具 |
| `oc.artifacts` | Ready | 产物管理 |
| `oc.approvals` | Ready | exec 审批 |
| `oc.models` | Ready | `models.list` + auth status |
| `oc.tasks` | Ready | Gateway task ledger |
| `oc.environments` | Partial | list 只读 |
| `oc.rawEvents()` | Ready | 高级用：原生事件 |
| `normalizeGatewayEvent()` | Ready | 原始事件 → SDK 事件格式转换 |

### 导出类型

`AgentRunParams`, `RunResult`, `RunStatus`, `OpenClawEvent`, `OpenClawEventType`, `GatewayEvent`, `OpenClawTransport`, `GatewayRequestOptions`, `SessionCreateParams`, `SessionSendParams`, `ArtifactSummary` / `Query` / `ListResult` / `GetResult` / `DownloadResult`, `TaskSummary`, `TaskStatus`, `TasksListParams` / `Result`, `TasksGetResult`, `TasksCancelResult`, `RuntimeSelection`, `EnvironmentSelection`, `WorkspaceSelection`, `ApprovalMode`

### ⚠️ SDK 安装口子（第 10 轮验证完成）

`packages/sdk/package.json` 标 `"version": "0.0.0-private"` + `"private": true`，不发到 npm 公开 registry。其依赖链 `@openclaw/gateway-client` / `@openclaw/gateway-protocol` 同样 private。主 `openclaw` npm 包的 `dist/` 只发 `plugin-sdk`，不发 App SDK。

**验证后的三条可行路径**（详见 §4.6）：

| 路径 | 描述 | 工作量 | 适合阶段 |
|---|---|:---:|---|
| **A. workspace + file:** | clone openclaw 仓库 + `pnpm install` + 在我们 package.json 写 `"@openclaw/sdk": "file:../openclaw/packages/sdk"` | 中 | MVP 之后 |
| **B. Direct WS** | 直接走 `ws://127.0.0.1:18789` 协议（`docs/gateway/protocol.md` 公开），自己实现 handshake + agent RPC | 大（参考 `transport.ts` 含 handshake/heartbeat/reconnect/seq gap ~1000+ 行） | 不推荐 |
| **C. ⭐ OpenAI-compat HTTP** | Gateway 开启 `/v1/chat/completions`，用标准 `openai` npm 包 + `model: "openclaw/<agentId>"` | 极小 | **PoC + MVP** |

### 4.5 `Agent.run()` 调用形式（Q2 闭合证据）

`packages/sdk/src/client.ts` 的 `buildAgentParams()` 把 `agentId` 作为 first-class 参数前向给 Gateway `agent` RPC（不依赖 channel binding）：

```typescript
function buildAgentParams(params: AgentRunParams): Record<string, unknown> {
  return {
    message: params.input,
    ...(params.agentId ? { agentId: params.agentId } : {}),
    ...(params.sessionKey ? { sessionKey: params.sessionKey } : {}),
    // model / provider / sessionId / thinking / ...
  };
}
```

官方调用范式（`docs/concepts/openclaw-sdk.md`）：

```typescript
const agent = await oc.agents.get("sarah");
const run = await agent.run({
  input: "用户消息",
  sessionKey: "dm:user-1:sarah",  // 显式 session key，按对话隔离
  timeoutMs: 30_000,
});
const result = await run.wait();
```

**关键发现**：
- `sessionKey` 默认行为 — 不传则同 agent 同 sender 会 collapse 到该 agent 的 `mainKey` session（multi-agent 文档原话："Direct chats collapse to `agent:<agentId>:<mainKey>`"）。我们需要为每个房间 / DM 显式传 `sessionKey`，建议格式 `dm:<userId>:<agentId>` / `room:<roomId>:<agentId>`
- per-run workspace override **不支持**（SDK 源 `assertNoUnsupportedRunOptions` 显式 throw），各 agent 的 workspace 必须在 `openclaw.json` 配置时确定

### 4.6 OpenAI-compat HTTP API 详情（Path C）

来源: `docs/gateway/openai-http-api.md`

**端点**：
```
POST http://127.0.0.1:18789/v1/chat/completions
Authorization: Bearer <gateway-token>
Content-Type: application/json
```

**Body 关键字段**：
```json
{
  "model": "openclaw/sarah",
  "messages": [...],
  "stream": true
}
```

也支持 header 覆盖：
- `x-openclaw-agent-id: sarah`
- `x-openclaw-model: anthropic/claude-sonnet-4-6`

**重要属性**：
- **同一内部 codepath**：原话 "Under the hood, requests are executed as a normal Gateway agent run (same codepath as `openclaw agent`)" → SOUL.md / AGENTS.md / 等 workspace 文件正常注入；route/permission/config 与原生路径一致
- **默认禁用**：要在 `openclaw.json` 显式开启
- **owner 信任级别**：原话 "treats chat turns on this endpoint as owner-sender turns" → 全 operator 权限，**只能 loopback / 私网，不能对外暴露**
- 限制：只覆盖 chat completions 表面，缺 `tools.invoke` / `artifacts` / `approvals` / per-run events 细颗粒（这些只 Path A 才有）

---

## 5. Gateway WS 协议

来源: `docs/gateway/protocol.md` + `docs/concepts/architecture.md`

- 传输: WebSocket text frames，JSON payload
- 默认端口: `127.0.0.1:18789`
- 第一帧必须是 `connect`，pre-connect 帧 ≤ 64 KiB
- 鉴权模式 (`gateway.auth.mode`)：shared-secret token / Tailscale / trusted-proxy / none
- Idempotency key 对副作用方法 (`send`, `agent`) 必填

帧格式:
```json
// Request
{"type":"req", "id":"...", "method":"...", "params":{...}}
// Response  
{"type":"res", "id":"...", "ok":true, "payload":{...}}
// Event (server push)
{"type":"event", "event":"...", "payload":{...}, "seq":N, "stateVersion":V}
```

握手流程: gateway 发 `connect.challenge` → client `req:connect` 含 device 签名 → gateway `res` 含 `hello-ok` 含 policy/features。

事件流: `agent`, `chat`, `presence`, `health`, `heartbeat`, `cron`, `tick`, `shutdown` 等。

操作员斜杠命令: `/status`, `/new`, `/reset`, `/compact`, `/think <level>`, `/verbose`, `/trace`, `/usage`, `/restart`, `/activation`

---

## 6. Workspace Bootstrap Files (每个 agent 自己的 persona 文件)

来源: `docs/concepts/agent-workspace.md` + `docs/concepts/system-prompt.md` + `docs/concepts/soul.md`

OpenClaw 每个 configured agent 都有一个 workspace 目录（默认 `~/.openclaw/workspace`，多 agent 时是 `agents.list[].workspace`），里面放一组标准 markdown bootstrap 文件，**启动 session 时自动注入到 system prompt**。

### 6.1 文件清单

| 文件 | 内容 | normal session 注入 | sub-agent session 注入 |
|---|---|:---:|:---:|
| `AGENTS.md` | 操作指令、行为规则、协作守则 | ✅ | ✅ |
| `TOOLS.md` | 本地工具使用习惯（仅引导，不控制 tool 可用性） | ✅ | ✅ |
| `SOUL.md` | 人格、tone、boundaries | ✅ | ❌ |
| `IDENTITY.md` | agent 名字、vibe、emoji | ✅ | ❌ |
| `USER.md` | 用户是谁、如何称呼 | ✅ | ❌ |
| `HEARTBEAT.md` | heartbeat run 的 checklist | ✅ (心跳启用时) | ❌ |
| `BOOT.md` | gateway 重启时自动跑的 startup checklist | ✅ (hooks 启用时) | ❌ |
| `BOOTSTRAP.md` | 一次性 first-run 仪式，跑完应删 | brand-new workspace only | ❌ |
| `MEMORY.md` | 长期记忆摘要（durable facts） | ✅ (条件性) | ❌ |
| `memory/YYYY-MM-DD.md` | 日记式记忆，按需走 `memory_search`/`memory_get` | 按需 | ❌ |
| `skills/` | workspace-local skills，最高优先级 | 按需 | 按需 |
| `canvas/` | Canvas UI 文件 | 不进 prompt | ❌ |

### 6.2 ⭐ Sub-agent session 的关键差异

`docs/concepts/system-prompt.md` 原话：

> "**Sub-agent sessions only inject `AGENTS.md` and `TOOLS.md`** (other bootstrap files are filtered out to keep the sub-agent context small)."

而且 sub-agent 用 `promptMode: minimal`，省略 Memory Recall / User Identity / Assistant Output Directives / Messaging / Silent Replies / Heartbeats 等 sections。

**对我们的影响**：通过 `sessions_spawn` 拉起的 Worker Run **拿不到 SOUL.md 人格**。如果要给 Worker 任何身份/限制信息，必须：
- 写进 `AGENTS.md` 或 `TOOLS.md`
- 直接塞进 `task` 字符串

### 6.3 大小限制

- 单文件: `agents.defaults.bootstrapMaxChars` 默认 12000 字符
- 总和: `agents.defaults.bootstrapTotalMaxChars` 默认 60000 字符
- 超长会被截断 + 注入截断警告（`bootstrapPromptTruncationWarning`: off/once/always）

### 6.4 SOUL.md 内容建议（来自 soul.md）

- ✅ tone / opinions / brevity / humor / boundaries / 默认 bluntness
- ❌ 生平介绍 / changelog / 安全政策 / 空泛 vibes
- 引用 OpenAI 提示工程指南：高层行为 + tone 放在高优先级指令层

### 6.5 内部 hook

`agent:bootstrap` hook 可以拦截这一步，动态替换/修改注入文件（例如换 persona 的 SOUL.md）。Phase 2 演化机制可借此实现"运行时换 persona 文件"，**MVP 用不到**。

---

## 7. SKILL.md (技能)

格式: frontmatter + Markdown body (实例: `skills/notion/SKILL.md`)

```yaml
---
name: notion
description: "..."
homepage: https://...
metadata:
  openclaw:
    emoji: 📝
    requires:
      anyBins: ["ntn", "curl"]
    primaryEnv: NOTION_API_TOKEN
    install:
      - id: node
        kind: node
        package: ntn
        bins: [ntn]
        label: "Install official Notion CLI (npm)"
---

# Notion

Prefer official `ntn` CLI. Use curl only when ...

## Setup
...

## Pages
...
```

- 内置 skill 全部在 `skills/` 目录
- 自定义 skill 放 workspace 的 skill 目录 (具体路径待查)
- 内容是 markdown 操作手册 + 可调用 CLI/API 的脚本片段

注册局: ClawHub (`https://clawhub.ai`) 是 skill 发现 registry

---

## 8. Memory 系统

来源: `docs/concepts/memory.md` + 子文档

OpenClaw 有多个 memory 实现 (按文档存在的子页推断):
- `memory-builtin.md` — 内置基础
- `memory-honcho.md` — Honcho 后端
- `memory-qmd.md` — QMD 后端
- `memory-lancedb.md` (在 `extensions/memory-lancedb/`) — LanceDB 向量
- `memory-search.md` — 搜索
- `active-memory` (extensions/) — 主动记忆

每 agent 有独立 workspace + session history，对应文档 `agent-workspace.md`。

我们的设计中 memory 第 1-2 层 (subagent 工作记忆 / 跨 session 持久) 由 OpenClaw 管，第 3-5 层 (跨 persona 知识 / 房间消息归档 / Main Agent 状态) 由我们 DB 管。

---

## 9. Multi-Agent 模式 (这一章重大修订 — 第 9 轮)

来源: `docs/concepts/multi-agent.md` + `docs/tools/subagents.md` + `docs/concepts/system-prompt.md` + 源码侦察

OpenClaw 提供**三种**完全不同的"多 agent"机制，**先前调研把它们混在一起了**。这一章按机制分清楚。

### 9.1 ⭐ Native Multi-Agent (我们要用的方案)

`docs/concepts/multi-agent.md` 原话：

> "Run multiple **isolated agents** — each with its own workspace, state directory (`agentDir`), and session history — in one running Gateway. An **agent** here is the full per-persona scope: workspace files, auth profiles, model registry, and session store."

配置方式：

```json5
{
  agents: {
    list: [
      { id: "main",   workspace: "~/.openclaw/workspace-main"  },
      { id: "sarah",  workspace: "~/.openclaw/workspace-sarah", model: "claude-sonnet-4-6" },
      { id: "alex",   workspace: "~/.openclaw/workspace-alex",  model: "claude-opus-4-7" },
      { id: "kai",    workspace: "~/.openclaw/workspace-kai",   model: "claude-sonnet-4-6" }
    ]
  },
  tools: {
    agentToAgent: { enabled: true, allow: ["main", "sarah", "alex", "kai"] }
  }
}
```

**每个 agent 拥有**：
- 独立 workspace（SOUL.md / AGENTS.md / USER.md / IDENTITY.md / TOOLS.md / MEMORY.md / skills/）
- 独立 `agentDir`（`~/.openclaw/agents/<id>/agent/`）含 auth-profiles
- 独立 session store（`~/.openclaw/agents/<id>/sessions/`）
- 可选独立 model / sandbox / tool allowlist

**路由**：
- 默认：channel binding（peer/guildId/accountId → agentId）— 我们不走 channel，不适用
- SDK 路径（待 100% 验证）：通过 `oc.agents.get(agentId).run({...})` 直接对单一 agent 触发 run
- 同 Gateway 内 agent 间通信：`tools.agentToAgent`（agent-to-agent 工具）

**约束**：
- **Auth profiles 不跨 agent 共享 OAuth refresh tokens**；可拷 portable 的 `api_key` profile
- "Never reuse `agentDir` across agents"
- 同 channel 同 sender DM 会 collapse 到 agent 的 `mainKey` session — 我们不走 channel 不受影响

**这是 visible SubAgent 的正确实现**：Sarah/Alex/Kai 各自是 `agents.list[]` 里的一项。

### 9.2 Sub-agent (sessions_spawn) — 我们的 Worker Run

来源: `docs/tools/subagents.md`

> "Sub-agents are background agent runs spawned from an existing agent run. They run in their own session (`agent:<agentId>:subagent:<uuid>`) and, when finished, **announce** their result back to the requester chat channel."

**特点**：
- session key 格式: `agent:<agentId>:subagent:<uuid>`
- 默认 isolated；**不自带 session tools**（要显式 allow）
- 完成后异步 announce 回 requester chat
- 每个 run 占独立 context + token usage
- 可配置 nesting depth (`agents.defaults.subagents.maxDepth`)
- 默认便宜 model: `agents.defaults.subagents.model`
- 加载哪些 workspace files：**只 AGENTS.md + TOOLS.md**（见 §6.2）
- promptMode = `minimal`

**用途**：Parallelize 研究/长任务/慢工具；不当 visible SubAgent 用。

### 9.3 ACP Agent (`spawnAcpDirect`) — 外部编码 harness

`src/agents/acp-spawn.ts` 定义。**用途澄清**：这是把 **Codex / Claude Code / Gemini CLI 等外部编码 harness** 通过 ACP（Agent Communication Protocol）拉起来当作 sub-agent，不是 OpenClaw 内部的"spawn 一个 agent"。

```typescript
spawnAcpDirect({
  task, agentId, resumeSessionId, model, runTimeoutSeconds,
  cwd, mode: "run" | "session", sandbox: "inherit" | "require",
  thread, streamTo
})
```

**Mode**:
- `run`: oneshot 任务
- `session`: 长期 thread-bound ACP session

**约束**：
- `resumeSessionId` 验证 `identity?.agentSessionId === resumeSessionId` — 仅原 spawner 能 resume（同一 OpenClaw agent context 内）
- ACP runtime 跑在 host 上，**不进 sandbox**
- Sandboxed session 不能 spawn ACP（要走 `runtime: "subagent"`）

**我们 MVP 不用**。如果将来要让 Kai (engineer persona) 调 Codex 跑代码，再用。

### 9.4 跨 agent / 跨 session 通信工具（OpenClaw 原生）

| 工具 | 能力 | 跨 agent? | 我们用途 |
|---|---|---|---|
| `sessions_history` | 读另一 session 历史（access control 内） | 单 agent 内 | Main agent 看 Sarah 历史 |
| `sessions_send` | 注入消息到另一 session | 单 agent 内 | 群聊调度时 Main 推给 Sarah |
| `sessions_send.a2a` | 多轮 ping-pong | 单 agent 内 | Loop 模式 |
| `sessions_list` | 列出可见 session | 单 agent 内 | — |
| `sessions_abort` | 终止 | 单 agent 内 | Kill switch |
| `sessions_spawn` | 创子 agent（见 §9.2） | 单 agent 内 | Worker Run |
| `tools.agentToAgent` | **跨 agent 调用**（off by default） | ✅ 跨 agent | Main agent 调 Sarah/Alex/Kai 的核心机制 |

### 9.5 Sub-agent Capabilities（来自 `src/agents/subagent-capabilities.ts`）

- `subagentRole` ∈ {`main`, `orchestrator`, `leaf`}
- `subagentControlScope` 当前只有 `"children"`（看不到 grandchildren）
- 这两条仅适用于 §9.2 sub-agent 场景，不影响 §9.1 native multi-agent

### 9.6 哪些"硬约束"还有效（更新版）

| 约束 | 适用场景 | 影响 |
|---|---|---|
| `resumeSessionId` only-spawner | ACP §9.3 | 不影响我们（不用 ACP） |
| `subagentControlScope = children only` | sub-agent §9.2 | Worker Run 是黑盒，要 visible subagent 主动 surface |
| `AgentConfig` 启动时加载，无 hot-reload | 全部 | 改 `openclaw.json` 要 `gateway restart`；workspace files 由 `agent:bootstrap` hook 可换 |
| `runTimeoutSeconds` 硬超时 | sub-agent / ACP | 长任务要主动续命 |
| ~~无共享 session / 房间原语~~ | 仍然成立但**不再是阻塞** | Main agent 用 `agentToAgent` 调 Sarah/Alex/Kai 各自的 session，等价于"群聊调度" |

---

## 10. 配置 / 数据布局

来源: `docs/openclaw-agent-runtime.md` + `docs/concepts/multi-agent.md` + `docs/concepts/agent-workspace.md`

### 10.1 状态目录（multi-agent 模式 — 我们要用的）

```
~/.openclaw/                            # 状态根 (OPENCLAW_STATE_DIR 可覆盖)
├── openclaw.json                       # 主配置（含 agents.list[]）
├── credentials/                        # channel/provider state（非 auth profile）
├── agents/
│   ├── main/
│   │   ├── agent/
│   │   │   ├── auth-profiles.json      # 该 agent 的模型 auth
│   │   │   └── codex-home/             # (可选) ACP runtime 自家目录
│   │   └── sessions/
│   │       ├── sessions.json           # session 索引
│   │       └── <session-id>.jsonl      # session transcript
│   ├── sarah/
│   │   ├── agent/...
│   │   └── sessions/...
│   ├── alex/...
│   └── kai/...
└── workspace-main/                     # main agent workspace (含 SOUL/AGENTS/USER/...)
└── workspace-sarah/
└── workspace-alex/
└── workspace-kai/
```

**约定**：`agents.list[].workspace` 通常对 `~/.openclaw/workspace-<id>/`，`agents.list[].agentDir` 对 `~/.openclaw/agents/<id>/agent/`。

### 10.2 我们的项目 workspace 放哪？

两种方案：
- **A. workspace 放本项目目录**：`agents.list[].workspace = "/Users/.../TelegramAgent/personas/sarah"`，跟代码 / git 一起管
- **B. workspace 跟 OpenClaw 默认位置**：`~/.openclaw/workspace-sarah`，跟 OpenClaw 状态一起

**倾向 A**：persona 文件就是产品资产，进 git 仓库；OpenClaw state 目录只保留 session + auth。

### 10.3 清理重置

- 全清: 删 `openclaw.json` + 所有 `agents/<id>/`（含 auth + sessions）+ `credentials/` + workspace 目录
- 仅清某个 agent sessions（保留 auth）: 删 `agents/<id>/sessions/`
- 仅清 workspace：删对应 `workspace-<id>/`

### 10.4 路径速查

```
config:        ~/.openclaw/openclaw.json  或 OPENCLAW_CONFIG_PATH
state root:    ~/.openclaw/                或 OPENCLAW_STATE_DIR
workspace:     agents.list[].workspace     或 ~/.openclaw/workspace-<id>
auth:          ~/.openclaw/agents/<id>/agent/auth-profiles.json
sessions:      ~/.openclaw/agents/<id>/sessions/sessions.json
transcripts:   ~/.openclaw/agents/<id>/sessions/<sessionId>.jsonl
```

---

## 11. Channels (我们用不到，但了解一下)

`extensions/` 下所有 IM channels:

WhatsApp, Telegram, Slack, Discord, Google Chat, Signal, iMessage, IRC, Microsoft Teams, Matrix, Feishu, LINE, Mattermost, Nextcloud Talk, Nostr, Synology Chat, Tlon, Twitch, Zalo, Zalo Personal, WeChat, QQ, WebChat

每个是独立 extension。我们 `openclaw.json` 中 `channels: {}` 全空即可。

DM 安全策略 (默认 `dmPolicy="pairing"`): 未知发送者收到配对码而非被 agent 处理。我们不开 channel，此机制不触发。

---

## 11.5 Prompt Modes (system-prompt 三种模式)

来源: `docs/concepts/system-prompt.md`

OpenClaw 给每个 run 设定一个 `promptMode`（runtime 内部，非 user-facing）：

| Mode | 用途 | 包含 | 排除 |
|---|---|---|---|
| `full` | 默认；normal session | 全部 sections | — |
| `minimal` | sub-agent (`sessions_spawn`) | Tooling / Safety / Skills / Workspace / Sandbox / Date / Runtime / 注入 context | Memory Recall / OpenClaw Self-Update / Model Aliases / User Identity / Assistant Output Directives / Messaging / Silent Replies / Heartbeats |
| `none` | 极少用 | 只 base identity line | 其他全部 |

`minimal` 下的额外注入 prompt 标 **"Subagent Context"** 而非 "Group Chat Context"。

**System prompt 结构** (full mode 主要 sections):
- Tooling
- Execution Bias
- Safety
- Skills (按需)
- OpenClaw Control / Self-Update
- Workspace (cwd)
- Documentation
- Workspace Files (注入的 bootstrap files)
- Sandbox (开启时)
- Current Date & Time
- Assistant Output Directives
- Heartbeats
- Runtime (host/OS/node/model/repo)
- Reasoning

**Prompt 装配**:
- `buildAgentSystemPrompt`: 纯渲染器，不读 global config
- `resolveAgentSystemPromptConfig`: 解析 per-agent prompt knobs
- Runtime adapter: 收集 live facts (tools/sandbox/channel/context files)

Provider plugins 可以贡献 cache-aware 的 prompt guidance（替换 `interaction_style`/`tool_call_style`/`execution_bias` 之一，或插 stable prefix / dynamic suffix）。

---

## 12. LLM Providers (我们要用)

`extensions/` 下的 provider 扩展:

`anthropic`, `anthropic-vertex`, `openai`, `azure-speech`, `deepseek`, `cerebras`, `chutes`, `cloudflare-ai-gateway`, `copilot`, `copilot-proxy`, `deepinfra`, `byteplus`, `arcee`, `alibaba`, `amazon-bedrock`, `amazon-bedrock-mantle`, `brave` (搜索), `comfy`, `pixverse`, ... (openrouter 应该有，需确认列表完整性)

文档: `docs/concepts/model-providers.md`, `docs/concepts/models.md`, `docs/concepts/model-failover.md`

模型 fail-over 是原生功能，配置 `agents.defaults.fallback` 之类字段。

---

## 13. Sandbox / 安全模型

来源: README + `docs/gateway/sandboxing.md` + `docs/gateway/security/`

- 默认: `main` session tools 跑在 host，full access (单用户场景 OK)
- Non-main session 可配 `agents.defaults.sandbox.mode: "non-main"` 用 Docker / SSH / OpenShell sandbox
- 典型 sandbox 默认: 允许 `bash` / `process` / `read` / `write` / `edit` / `sessions_*`；禁 `browser` / `canvas` / `nodes` / `cron` / 各 IM 工具

我们本地单用户 MVP 可不开 sandbox。

---

## 14. CLI 速查

```bash
# Daemon
openclaw onboard --install-daemon
openclaw gateway status
openclaw gateway stop
openclaw gateway --port 18789 --verbose

# 直接对话
openclaw agent --message "Hello" --thinking high

# 发消息 (通过 channel)
openclaw message send --target +1234567890 --message "..."

# Pairing
openclaw pairing approve <channel> <code>

# 诊断
openclaw doctor

# 升级
openclaw onboard         # 或 npm i -g openclaw@latest
```

---

## 15. 待验证 / Open 问题

### 已闭合

| # | 问题 | 结论 | 关闭日期 |
|---|---|---|---|
| ~~1~~ | `@openclaw/sdk` 能否外部 npm install | **不能直接 install**，但 PoC/MVP 走 Path C (OpenAI-compat HTTP)，未来需要细颗粒事件再切 Path A (workspace + file:)。详见 §4.4 | 2026-05-30 |
| ~~2~~ | SDK 能否直接按 `agentId` 触发 normal session run（不走 channel binding） | **YES**，`buildAgentParams()` 把 `agentId` 作为 first-class 参数前向给 Gateway agent RPC；OpenAI HTTP 端点同样支持 `model: "openclaw/<agentId>"`。详见 §4.5 / §4.6 | 2026-05-30 |
| ~~9~~ | `spawnAcpDirect(mode:"session")` 是 normal session 吗，SOUL.md 加载吗 | **问题前提错了**：`spawnAcpDirect` 是 ACP 外部 harness（Codex/Claude Code），不是我们要的方式。Visible SubAgent 用 §9.1 native multi-agent 模式，SOUL.md 自动加载 | 2026-05-30 |
| ~~10~~ | sub-agent (`sessions_spawn`) 加载哪些 workspace files | **只 AGENTS.md + TOOLS.md**（§6.2 引用 system-prompt.md） | 2026-05-30 |
| ~~11~~ | `memory_search` / `memory_get` 工具需要哪种 embedding provider 配置才能跑 | **接 `agents.defaults.memorySearch = {provider: "openai-compatible", model: "bge-m3", remote: {baseUrl, apiKey}}`**。Ruidong 的 bge-m3 是 OpenAI-format 1024 维 embedding。实证端到端通过：sarah 主动调 memory_search → 向量检索 → 给出 source ref `memory/2026-05-30.md#L15`。详见 §18 | 2026-05-30 |

### 仍开放（按优先级）

| # | 问题 | 影响 |
|---|---|---|
| 3 | `tools.agentToAgent` 调用是同步等回复还是异步 push | 决定 Main Agent 调度群聊的代码风格 |
| 4 | 多 agent 是否要每个独立 OpenRouter API key profile，还是可共享 | `auth-profiles.json` 是 per-agent；warning 说 "Never reuse `agentDir`"，但 portable api_key profile 可拷 |
| 5 | `openclaw agents add` CLI 是否真能运行时增删 agent（Phase 2 用户自定义 persona 用） | 影响 Phase 2 自定义 persona 路径 |
| 6 | `openclaw.json` 完整 schema（用 zod） | 我们要写最小化配置 |
| 7 | `agent:bootstrap` hook 接口（动态替换 SOUL.md 等 workspace 文件） | Phase 2 evolution 运行时换 persona 文件的备选方案 |
| 8 | Gateway 同时跑多个 client（我们后端 + Web UI 直连）是否冲突 | 影响架构 |
| 9 | 同一 Gateway 多 agent 跑同一 OpenRouter 账号会不会被限流 | 性能 + 成本 |
| 10 | `sessions_history` 跨 agent 是否能读（access control 范围） | Main Agent 跨 persona 反思可行性 |

---

## 16. 参考链接

- 主仓库: https://github.com/openclaw/openclaw
- 官方文档站: https://docs.openclaw.ai (Claude Code WebFetch 受限，需 curl raw GitHub)
- DeepWiki: https://deepwiki.com/openclaw/openclaw
- Discord: https://discord.gg/clawd
- Skills registry: https://clawhub.ai
- 关键文档原文路径 (raw GitHub):
  - `docs/concepts/openclaw-sdk.md`
  - `docs/concepts/architecture.md`
  - `docs/gateway/protocol.md`
  - `docs/concepts/soul.md`
  - `docs/concepts/multi-agent.md`
  - `docs/concepts/agent-runtimes.md`
  - `docs/openclaw-agent-runtime.md`

---

## 17. Memory Search / Embedding 配置（第 13 轮实证）

### 17.1 OpenClaw 内置 memory 系统架构

每个 configured agent 独立的 memory store：`~/.openclaw/memory/<agentId>.sqlite`，含：
- **FTS** (BM25 keyword search) — 默认开启，零配置
- **Vector store** (semantic search via embeddings) — 需要配 embedding provider
- **MMR / temporal decay** — 可选优化（large note history 时启用）

并行跑 vector + BM25，weighted merge。embeddings 没配也能跑（degraded 模式：FTS + lexical ranking）。

### 17.2 Embedding Provider 选项

来源：`docs/reference/memory-config.md`

| Provider ID | API Key 必需 | 备注 |
|---|---|---|
| `bedrock` | 否 | AWS credential chain |
| `deepinfra` | 是 | Default model: `BAAI/bge-m3` |
| `gemini` | 是 | 支持图像/音频 indexing |
| `github-copilot` | 否 | Copilot 订阅 |
| `local` | 否 | GGUF 本地模型，~0.6 GB 下载 |
| `mistral` | 是 | |
| `ollama` | 否 | 本地/自部署 |
| `openai` | 是 | 默认 |
| `openai-compatible` | 通常是 | ⭐ 通用 `/v1/embeddings` |
| `voyage` | 是 | |

### 17.3 Ruidong bge-m3 接法（实证有效）

```json5
{
  agents: {
    defaults: {
      memorySearch: {
        provider: "openai-compatible",
        model: "bge-m3",
        remote: {
          baseUrl: "https://iruidong.com/v1/",   // 注意尾部 /
          apiKey: "sk-..."                        // 或 ${RUIDONG_API_KEY}
        }
      }
    }
  }
}
```

- bge-m3 是对称 embedding，**不需要** `queryInputType` / `documentInputType` 配置
- ruidong /v1/embeddings 返回 1024 维向量（实测）
- 每 agent 各自独立 memory store，无需重复配；`agents.defaults.memorySearch` 全 inherit

### 17.4 实证流程

1. **配 provider** → `openclaw gateway restart` → `openclaw memory status --deep` 看 `Embeddings: ready` + `Vector store: ready`
2. **写 memory 文件** → `personas/<id>/memory/YYYY-MM-DD.md`（普通 markdown，每个 section 会被切 chunk）
3. **建索引** → `openclaw memory index --force` → `Indexed: N/N files · M chunks`
4. **触发 retrieve** → agent 通过 chat 收到需要查记忆的问题 → 主动调 `memory_search` 工具 → 返回时含 source ref（如 `memory/2026-05-30.md#L15`）

### 17.5 注意事项

- ⚠ `memory_search` 是 model 主动决策是否调用 — 如果 system prompt 里已经能答（如 USER.md），model 可能直接答不去 search。query 里用"查一下记忆 / 你之前记过的" 是更稳的触发
- ⚠ `models.providers.<id>` 里的 `apiKey` 跟 `memorySearch.remote.apiKey` **不共享**；ruidong embeddings 要单独配（即使 baseUrl 一样）
- ⚠ 改 embedding model 或 dimension 会触发自动 full reindex
- ✅ 索引内容 dirty 后 `--force` 重建；增量索引由 OpenClaw 自动管

---

## 18. 调研方法备忘

GitHub API 可达，但 `git clone` 在当前环境会超时 (codeload.github.com)。访问仓库内容用:

```bash
# 列目录
curl -s --max-time 15 "https://api.github.com/repos/openclaw/openclaw/contents/<path>" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(x['type'][0], x['name']) for x in d]"

# 读文件
curl -s --max-time 15 "https://raw.githubusercontent.com/openclaw/openclaw/main/<path>"
```

下次想验证更深的问题时，可派 Explore agent 用这套方法批量取。
