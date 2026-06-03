> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# Context、Memory 与信息传递

## 核心原则

Main Agent 可以管理信息流，但不应该默认读取和传播所有原始内容。

SubAgent 之间默认隔离；跨 Agent 传递的是经过产品层授权和裁剪的 ContextPack，而不是随便共享 raw transcript。

## ContextPack

ContextPack 是每次发给 SubAgent 或 Main 的最小必要上下文。

```ts
type ContextPack = {
  id: string
  purpose: 'dm_turn' | 'group_round' | 'review' | 'worker' | 'reflection'
  targetAgentId: string
  conversationId?: string
  roomGoal?: string
  userRequest: string
  recentPublicMessages: MessageSummary[]
  activeArtifacts: ArtifactSummary[]
  activeRuns: RunSummary[]
  relevantMemories: MemorySnippet[]
  permissionSnapshot: PermissionSnapshot
  budgetSnapshot?: BudgetSnapshot
  privateSnippets?: UserApprovedPrivateSnippet[]
  redactions: RedactionNotice[]
}
```

## 单聊 Context

DM 给 SubAgent 的上下文可以包含：

```text
该 DM 的近期消息
该 SubAgent 对用户的长期记忆
用户明确共享给该 SubAgent 的文件/artifact
该 SubAgent 自己的 workspace 摘要
```

默认不包含：

```text
用户和其他 SubAgent 的私聊
其他 room 的未共享内容
其他 SubAgent 的 memory
```

## 群聊 Context

Room 中给 SubAgent 的上下文可以包含：

```text
room goal
room recent public messages
room shared artifacts
room member list
与该任务相关的公开 memory
```

如果需要引用私聊内容，必须满足：

```text
用户显式分享
或者私聊内容已经被用户转成 room artifact
或者只传递经过授权的摘要
```

## SubAgent 之间的信息传递

Main Agent 可以把 SubAgent A 的输出传给 SubAgent B，但必须以结构化摘要传递。

```text
不要：把 A 的完整 raw transcript 贴给 B
应该：把 A 的 finding/report/summary 传给 B
```

示例：

```ts
type AgentHandoff = {
  fromAgentId: string
  toAgentId: string
  reason: string
  contentType: 'finding' | 'artifact' | 'question' | 'constraint'
  content: string
  sourceRefs: string[]
  visibility: 'room' | 'private_to_target' | 'audit_only'
}
```

## Memory 分层

### 1. Product Memory

产品层保存的可查询记忆：

```text
用户偏好
项目事实
room summary
artifact index
permission decisions
SubAgent relationship facts
```

### 2. Agent Memory

小人自己的长期记忆：

```text
该小人与用户的互动偏好
该小人的专业经验
该小人的历史工作成果
该小人的失败模式
```

### 3. Runtime Memory

OpenClaw/其他 harness 内部的 memory/session 文件。

只作为 runtime 状态，不是唯一主权来源。

## Memory 写入规则

默认不要把每条聊天都写入长期记忆。

写入触发：

```text
用户明确说“记住”
长期偏好稳定出现多次
项目事实发生变化
review 产生重要结论
用户批准分享/保存
Main Supervisor 生成低风险 memory patch
```

## Memory 摘要格式

```markdown
# Memory Note

scope: user | agent | room | project
target: Bram
confidence: high | medium | low
source_refs:
  - message:xxx
  - artifact:yyy

## Fact
用户偏好先看可执行 MVP，再讨论长期架构。

## Use When
当 Bram 给工程建议时，优先给最短实现路径和风险点。
```

## Privacy Redaction

ContextPack 必须记录 redaction，而不是假装上下文完整。

```ts
type RedactionNotice = {
  sourceType: 'dm' | 'room' | 'artifact' | 'memory'
  reason: 'private' | 'not_relevant' | 'permission_denied' | 'too_large'
  summaryForAudit: string
}
```

这样用户打开审计面板时能看到：

```text
没有把你和 Iris 的私聊传给 Bram。
只传递了你手动分享进 room 的摘要。
```
