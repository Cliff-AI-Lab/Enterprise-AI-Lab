> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# 编排协议

## 协议总览

| 协议 | 触发 | Main Agent 是否介入 | 输出 |
|---|---|---:|---|
| DM Direct | 单聊 | 否，默认不介入 | SubAgent message |
| Mention Route | 群里 @ 某人 | 轻量规则 | 被 @ 的 SubAgent message |
| Selected Speakers | 开放问题 | 是 | 1-N 个 SubAgent messages |
| Round Robin | 头脑风暴 | 是 | 依次发言 + summary |
| Parallel Then Merge | Review/研究 | 是 | Findings + artifact |
| Debate Then Summary | 有冲突 | 是，最多一轮 | 对比 + verdict |
| Worker Delegation | 需要工具/代码/搜索 | SubAgent 或 Main 触发 | artifact/report |

## 1. DM Direct

单聊默认路径。

```text
User → Router → Target SubAgent → User
```

Main Agent 不应该每条消息都思考。

伪代码：

```ts
async function handleDmMessage(userMessage, targetAgent) {
  await db.save(userMessage)
  const session = await runtime.ensurePersonaSession(targetAgent)
  const result = await runtime.runTurn({
    session,
    input: userMessage,
    contextPack: buildDmContextPack(userMessage, targetAgent),
  })
  return publishSubAgentMessage(result)
}
```

## 2. Mention Route

群里用户明确 @Bram，就发给 Bram。

```text
User: @Bram 这个接口怎么拆？
→ Bram 回复
→ Main 不需要深度介入
```

Main/Router 只做：

```text
权限检查
上下文裁剪
状态检查
是否需要 worker
```

## 3. Selected Speakers

用户没有明确 @，但问题明显适合某些小人。

```text
User: 帮我看看这个页面和实现有没有问题
→ Main 选择 Luna + Bram
```

选择原则：

```text
最多 3 个 SubAgent
优先当前 room 成员
优先最近参与者
避免每次都全员发言
```

## 4. Round Robin

适合 brainstorming。

协议：

```text
Main 设定目标
每个 SubAgent 一轮
每人最多 N 条
不允许重复上一人的观点
最后生成 Summary Card
```

默认限制：

```text
max_agents = 4
max_rounds = 1
max_message_per_agent_per_round = 1
```

## 5. Parallel Then Merge

适合 review 和研究。

```text
Main 同时给多个 SubAgent 不同 ContextPack
每个 SubAgent 独立工作
Main 收集 findings
Main 生成 artifact 或选择哪些消息展示
```

优点：

```text
减少互相污染
速度快
每个小人专注自己的专业视角
更容易审计
```

## 6. Debate Then Summary

只在发现明显冲突时启动。

触发条件：

```text
两个 SubAgent 给出相反结论
review verdict 不一致
一个说必须改，另一个说不该改
证据冲突
```

限制：

```text
最多一轮 debate
只讨论冲突点
必须输出最终 verdict 或 uncertainty
```

## 7. Worker Delegation

当 SubAgent 需要工具型任务时，spawn Worker Run。

```text
Bram → code grep / tests / diff worker
Echo → web/source search worker
Luna → screenshot analysis / moodboard worker
Main → merge / summarize worker
```

Worker 的结果通常不直接显示给用户，而是返回给请求方 SubAgent 或 Main。

## 8. 终止循环规则

Main Agent 必须具备强制终止能力。

终止条件：

```text
达到 max_rounds
连续两条没有新增信息
SubAgent 重复同一建议
用户问题已被回答
成本/时间超过预算
发生权限等待
发生工具失败且无替代路径
```

终止输出：

```text
Summary Card
Next Action
等待用户选择
```

## 9. 消息可见性

每个 run 的输出分三类：

```text
public_message    展示在聊天流
system_card       展示为总结/产物卡
hidden_trace      只进审计面板
```

Main Agent 的中间调度默认是 `hidden_trace`。
