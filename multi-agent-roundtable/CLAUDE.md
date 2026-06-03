# TelegramAgent

本地单用户、Telegram 风格的 AI 助手 web 应用。3 个职业向 persona（Sarah 文案 / Alex PM / Kai 工程师）+ 1 个隐藏 Main。基于 OpenClaw runtime；前端 React + Vite，后端 Hono + node:sqlite。

> 项目状态：**MVP / Phase 1**。单聊跑通。群聊 / Audit / Permission / Evolution 是开放面（见 `ISSUE.md`）。

## 跑得起来什么

| 能力 | 状态 |
|---|---|
| 单聊 sarah / alex / kai（DM） | ✅ Path C `/v1/chat/completions` |
| SSE 流式输出 | ✅ AgentUX event 协议 |
| SQLite 持久化（users / agent_profiles / rooms / messages） | ✅ |
| 头像 / 表情 placeholder / status dot（online/idle/offline） | ✅ |
| 后端注入当前时间（`<env>` 块） | ✅ |
| Memory search（`memory_search` 工具 + bge-m3 embedding） | ✅ OpenClaw 自带，已配 |
| 每 persona 的 OpenClaw skill（人设化工具集） | ✅ allowlist 收窄（见下） |
| 接龙房 / 头脑风暴房 / 打磨房 | ⚠️ UI 在，未接 LLM |
| Convene / Review tab | ❌ disabled |
| Audit Panel / Permission Gateway / Evolution loop | ❌ 未实现 |

## 怎么启动

需要同时跑 3 个进程：

```bash
# 1. OpenClaw Gateway（监听 127.0.0.1:18789）
openclaw gateway start

# 2. Backend（监听 127.0.0.1:18791）
cd backend && pnpm dev

# 3. Frontend（监听 127.0.0.1:5183）
cd frontend && pnpm dev
```

打开 http://127.0.0.1:5183。

环境变量（`backend/.env`）：
- `OPENCLAW_BASE_URL` / `OPENCLAW_GATEWAY_TOKEN` — Gateway 连接
- `TELEGRAM_AGENT_DB` — SQLite 文件路径
- `TELEGRAM_AGENT_TZ` — 注入 envBlock 用，默认 `Asia/Shanghai`
- `PORT` — 后端端口

## 想干什么 → 看哪儿

| 任务 | 入口 |
|---|---|
| 改 persona 人设 / 边界 / 语气 | `personas/<id>/SOUL.md` → 重启 OpenClaw |
| 改 persona 自我介绍 / 名片 | `personas/<id>/IDENTITY.md` → 重启 OpenClaw |
| 加新 persona | 新建 `personas/<id>/{IDENTITY,SOUL,USER,AGENTS,TOOLS,HEARTBEAT}.md` + 改 `openclaw.json` agents.list + 重启 |
| 给 persona 加/换 skill | 改 `~/.openclaw/openclaw.json` 里 `agents.list[].skills` allowlist + 重启 OpenClaw |
| 装新 skill | ClawHub：`openclaw skills install <slug> --agent <id>`；personal 池：`~/.agents/skills/<id>/SKILL.md` 直接 mkdir |
| 看 skill 状态 | `openclaw skills list --agent <id>` 看 ready/excluded 清单 |
| 改前端 UI | `frontend/src/App.tsx`（3700 行，**仍是 monolith**，看 `ISSUE.md`） |
| 改前端样式 | `frontend/src/styles.css` |
| 加后端 API | `backend/src/routes/*.ts` + 在 `server.ts` 挂载 |
| 改 DB schema | `backend/src/db.ts`（内联 DDL，**没有独立 schema.sql**） |
| 改注入给 LLM 的环境块（时间 / 共享规则等） | `backend/src/envBlock.ts` |
| 看当前架构详情 | `docs/00_README.md` |
| 看历史决策 / "为什么这样" | `temp_design.md`（按"第 N 轮"组织，13 轮迭代积累） |
| 看 OpenClaw 调研细节 | `openclaw_research.md` |
| 看遗留问题 | `ISSUE.md` |

## 关键约定

### Persona ID 是短形式
4 个：`main` / `sarah` / `alex` / `kai`。OpenClaw 用、DB 用、前端用——全短。
`main` 隐藏（`agent_profiles.hidden = 1`），不在 contact list 出现。

### Persona workspace 文件
每个 persona 在 `personas/<id>/` 下：

| 文件 | 含 | 改动频率 |
|---|---|---|
| `IDENTITY.md` | 名片：name / role / vibe / 自我介绍模板 | 极少 |
| `SOUL.md` | 行为：Voice / 工作原则 / 边界 / Anti-AI-tone | 频繁 |
| `USER.md` | 用户画像 / 互动偏好 | 偶尔 |
| `AGENTS.md` | 跨 agent 协作（哪些事是别人的） | 偶尔 |
| `TOOLS.md` | 工具使用习惯 | 偶尔 |
| `HEARTBEAT.md` | 定时任务（默认空） | 偶尔 |

⚠️ **OpenClaw 启动时一次性 load 进 system prompt，热重载不工作。** 改完要 `openclaw gateway restart`。

### envBlock 是后端动态注入层
`backend/src/envBlock.ts` 每次请求向 OpenClaw 前 prepend 一段 `<env>` 块。当前只有"当前时间"；未来加跨 agent 共享规则、当前房间、用户状态都从这里走，不要往 SOUL.md 复制三遍。

### Path C：通过 OpenAI-compat 调 OpenClaw
后端 → Gateway 用 `POST /v1/chat/completions`，`model: "openclaw/<agentId>"`，`user: "me:<agentId>"` 派生 sessionKey。MVP 不用 SDK / Path A。

### Skills：per-agent allowlist
当前给每个 persona 收窄了一份 skill 清单（progressive loading，每个 skill ~100 tokens 注入 system prompt 触发 → 真要用了才 load body）：

| Persona | Skills | 来源 |
|---|---|---|
| `main` | `dispatching-parallel-agents` | personal `~/.agents/skills/` |
| `sarah` | `minnow-writing`, `clarity-and-grace` | workspace `personas/sarah-writer/skills/`（ClawHub 下载） |
| `alex` | `prd`, `project-spec` | personal |
| `kai` | `systematic-debugging`, `verification-before-completion`, `feature-guardian` | personal |

规则：`agents.list[].skills` 是**显式 allowlist 替换**（不是 merge）；省略字段才继承 defaults。改完**必须重启 OpenClaw Gateway** 才生效。

### ⚠️ openclaw.json 有两份
- **`~/.openclaw/openclaw.json`** — Gateway **实际读**的（gateway.auth.token / session / agents.list 真正生效）
- **`./openclaw.json`** — 项目里这份是早期 PoC 副本，**没被加载**，但作为 git 可追溯的源真保留

改 agents.list / skills allowlist / providers 时记得**主改 `~/.openclaw/openclaw.json`**，再同步项目副本（手抄）。

## 我做事的方式（给未来 session）

参考 `~/.claude/CLAUDE.md` 全局规则。重申几条：

- **直接说事**，不堆 PPT 排版 / 不写"作为 X" / 不写"希望对你有帮助"
- **改 A 别动 B**——不顺手重构无关代码
- **50 行能解决就不写 200 行**
- **不加用户没要的"以防万一"抽象**——schema 字段、配置开关、回退分支
- **测试自己跑完**——curl 实测 / 浏览器打开看，不把验证推给用户
- **改设计**先翻 `temp_design.md` 找最近一轮的判断，别从零想

## docs/ 子目录说明

`docs/00_README.md` 是**当前实现快照**（替代了旧 GPT 版本）。

`docs/01_*.md ~ 12_*.md` 是 2026-05-29 GPT 生成的早期设计，**已 stale**（基于"Main spawn Bram/Nova/Atlas/Iris"模型，第 9 轮被原生 multi-agent 推翻）。每个文件顶部有 `[STALE]` banner。保留作为历史参考，要看现在的设计去 `temp_design.md`。

## 链外资源

- OpenClaw docs / source 入口：`openclaw_research.md §1-§3`
- ruidong provider（OpenAI-compat backend）：`openclaw_research.md §12`
