> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# OpenClaw Runtime 方案

## 目标

第一版使用 OpenClaw 作为主要 runtime/harness：隐藏 Main Agent 负责后台编排，可见 SubAgent 作为用户可聊天的小人，Worker Run 负责临时任务。

但产品层必须通过 `AgentRuntimeAdapter` 调用 OpenClaw，避免把产品身份绑定到底层 session/run。

## Runtime 分层

```text
Product SubAgent
  ↓ maps to
Runtime Agent / Persona Session
  ↓ may spawn
Worker Run / raw sub-agent / external harness
```

产品层不应该保存：

```text
Adam = 某个固定 childSessionKey
Bram = 某个固定 runId
```

产品层应该保存：

```text
Bram = AgentInstance
Bram 当前运行态 = PersonaSession(runtimeSessionKey 可变)
```

## Main Agent 用法

Main Agent 是隐藏的 runtime operator。

它可以拥有工具：

```text
list agents/sessions
send message to SubAgent session
spawn worker
read bounded session summaries
create summary artifact
cancel/stop run
write audit event
propose evolution patch
```

它不应该拥有默认权限：

```text
读取所有 DM raw transcript
绕过用户授权读取私密文件
直接改工具权限
直接改 harness 代码
```

## SubAgent 初始化

每个 SubAgent 需要模板：

```text
SOUL.md      人格、价值观、边界
AGENTS.md    工作职责、协作规则
TOOLS.md     工具使用规则
MEMORY.md    长期偏好和事实
skills/      专业能力
model        默认模型
permissions 允许/拒绝/需审批
workspace    独立工作区
```

产品层保存 canonical 版本；runtime workspace 保存运行时版本。

## Spawn/Lazy Resume 策略

不要追求所有 SubAgent 永久常驻。正确目标是：可恢复、身份稳定、记忆稳定。

```text
用户打开 Bram DM
→ ensure AgentInstance exists
→ ensure workspace/memory exists
→ ensure PersonaSession active or recoverable
→ route turn to Bram
```

如果 runtime session 丢失：

```text
重新 provision session
注入 canonical soul + relevant memory
恢复 recent conversation summary
继续聊天
```

## AgentRuntimeAdapter

```ts
interface AgentRuntimeAdapter {
  ensureAgent(input: EnsureAgentInput): Promise<RuntimeAgentRef>
  ensurePersonaSession(input: EnsureSessionInput): Promise<RuntimeSessionRef>
  runTurn(input: RunTurnInput): Promise<RunTurnResult>
  sendToSession(input: SendToSessionInput): Promise<RunTurnResult>
  spawnWorker(input: SpawnWorkerInput): Promise<RunRef>
  getRunStatus(runId: string): Promise<RunStatus>
  getRunResult(runId: string): Promise<RunResult>
  cancelRun(runId: string): Promise<void>
}
```

## Model Routing

SubAgent 可以使用不同模型。

推荐策略：

```text
Bram / code      GPT / Claude / Codex-style
Luna / design    multimodal model
Echo / research  search + long context model
Iris / writing   DeepSeek / Claude-style
Atlas / planning reasoning model
Main / routing   small fast model by default
Main / merge     stronger model only when needed
```

## Main Agent 调用成本控制

Main 不应每条消息介入。

```text
DM direct: no Main LLM
Mention route: rules / small model only if ambiguous
Convene: Main coordinator
Review: Main coordinator + merge
Reflection: low-frequency supervisor
```

## 必须验证的 OpenClaw 能力

落地前用 demo/source 证明：

```text
1. 能否按 agentId/template/soul/tools/model/permissions 拉起 SubAgent
2. session 丢失后能否恢复 workspace/memory
3. Main 是否能可靠发送消息给多个 child sessions
4. Main 能读到什么范围的 child report/session history
5. Context isolated/fork 的实际行为
6. worker run 的 timeout/cancel/retry 是否可控
7. 不同 agent 的 tool permission 是否真隔离
8. 外部 harness 是否绕过 OpenClaw sandbox
9. 审计事件能否完整还原 route/context/tool/run
```

## 关键风险

### 风险 1：raw sub-agent 不是长期人格容器

解决：产品层抽象 `SubAgent`，runtime 可用 configured agent/session/raw child session 实现，但不绑定死。

### 风险 2：Main 变成瓶颈

解决：DM 直达；Main 只在 Convene/Review/异常/进化时介入。

### 风险 3：权限边界不清

解决：Product Permission Gateway 在 OpenClaw 之外再做一层，尤其是文件、shell、凭证、外部 harness。

### 风险 4：人格同质化

解决：Main 只调度，不替专业 SubAgent 判断；每个 SubAgent 独立 soul/memory/skills/model。
