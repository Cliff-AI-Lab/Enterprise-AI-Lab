> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# Agent 模型定义

## 术语

| 名称 | 产品含义 | 是否用户可见 | 生命周期 |
|---|---|---:|---|
| Main Agent | 隐藏后台编排者 | 否 | 长期 |
| SubAgent / Child Agent | 用户可见小人 | 是 | 长期身份，运行态可重启 |
| Worker Run | 临时后台任务 | 否 | 短期 |
| Persona Session | 某个小人在某个会话里的运行态 | 间接可见 | 可恢复/可替换 |
| Runtime Session | OpenClaw/Codex 等底层 session | 否 | runtime 决定 |

## Main Agent

Main Agent 是隐藏操作系统。

### 可以做

```text
选择参与的 SubAgent
构造 ContextPack
控制群聊轮数
汇总多 Agent 输出
触发 worker run
生成审计事件
发现失败模式
生成 EvolutionPatch
```

### 不可以做

```text
在主聊天中以人格发言
默认读取所有私聊 raw transcript
绕过权限访问工具/文件/凭证
直接永久修改高风险配置
让所有小人的判断同质化
```

## SubAgent / Child Agent

SubAgent 是用户真正交流的对象。

一个 SubAgent 应该包含：

```ts
type AgentProfile = {
  id: string
  name: string
  avatarUrl?: string
  role: 'builder' | 'designer' | 'researcher' | 'writer' | 'planner' | string
  soulTemplate: string
  defaultModel: string
  defaultSkills: string[]
  defaultTools: string[]
  defaultPermissions: PermissionPolicy
  defaultSandboxPolicy: SandboxPolicy
}

type AgentInstance = {
  id: string
  userId: string
  profileId: string
  displayName: string
  runtimeType: 'openclaw' | 'codex' | 'claude_code' | 'hermes' | 'custom'
  runtimeAgentId?: string
  workspaceRef: string
  memoryRef: string
  status: AgentStatus
  createdAt: string
  lastActiveAt: string
}
```

## Persona Session

Persona Session 是 SubAgent 在一个 DM 或 room 里的会话运行态。

```ts
type PersonaSession = {
  id: string
  agentInstanceId: string
  conversationId: string
  parentMainSessionId?: string
  runtimeSessionKey?: string
  mode: 'dm' | 'room' | 'review'
  state: 'active' | 'idle' | 'closed' | 'recovering'
  lastContextPackId?: string
}
```

关键点：

```text
SubAgent 身份 ≠ PersonaSession
PersonaSession ≠ Runtime Run
Runtime Run 可重启，SubAgent 身份不丢
```

## Worker Run

Worker Run 是短期劳动力，不是小人身份。

```ts
type WorkerRun = {
  id: string
  parentRunId?: string
  requesterAgentId: string
  runtime: 'openclaw' | 'codex' | 'claude_code' | 'e2b' | 'custom'
  task: string
  model?: string
  sandboxPolicy: SandboxPolicy
  toolPolicy: ToolPolicy
  status: 'queued' | 'running' | 'waiting_permission' | 'succeeded' | 'failed' | 'cancelled'
  resultArtifactIds: string[]
}
```

典型例子：

```text
Bram spawn code review worker
Echo spawn source search worker
Luna spawn visual alternatives worker
Main spawn merge/summarize worker
```

## Agent 状态

不要把状态直接等同于进程存活。

```ts
type AgentStatus =
  | 'online'    // 可立即响应
  | 'thinking'  // 正在生成回复
  | 'working'   // 正在执行工具/worker
  | 'waiting'   // 等用户批准
  | 'away'      // 降级、idle、低优先级
  | 'offline'   // 禁用、不可用、未 provision
```

状态来源：

```text
queue length
active run
permission wait
provider health
runtime availability
user setting
rate limit
```

## 推荐的初始小人

| 名字 | 角色 | 默认强项 | 模型策略 |
|---|---|---|---|
| Bram | Builder / Engineer | 代码、实现、review | GPT/Claude/Codex 类 |
| Luna | Designer | UI、视觉、交互 | 多模态/视觉强模型 |
| Echo | Researcher | 证据、资料、引用 | 搜索 + 长上下文模型 |
| Iris | Writer | 表达、文案、压缩 | DeepSeek/Claude 类 |
| Atlas | Planner | 规划、拆解、风险 | 推理强模型 |
| Nova | Coordinator-like visible helper 可选 | 轻量主持 | 小模型 |

Nova 如果作为可见角色存在，要和隐藏 Main Agent 严格区分。Nova 可以是“房间主持人”，但不是后台上帝。
