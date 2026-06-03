> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# 核心决策

## 1. 产品是 SubAgent-first，不是 Main-Agent-first

用户不会和主 Agent 聊天。用户看到的是 Bram、Nova、Atlas、Iris 这样的可聊天小人；主 Agent 只在后台做系统级工作。

```text
不是：User ↔ Main Agent → spawn worker
而是：User ↔ SubAgent 小人；Main Agent 在幕后编排 SubAgent graph
```

## 2. Main Agent 永远不作为聊天成员出现

Main Agent 不能被 @，不能在群里发人格化消息，也不能替某个小人说话。

允许出现的是系统卡片，例如：

```text
Summary Card
- Bram 发现 2 个实现风险
- Iris 发现 1 个表达问题
- Atlas 建议先做第 2 个方案
```

不允许出现的是：

```text
Main Agent: 我来总结一下大家的观点……
God: 我认为你应该……
Coordinator: 我已经帮你调度了 Bram 和 Iris……
```

## 3. SubAgent 是长期身份，不是一次 run

一个小人的身份由产品层定义：头像、名字、人格、skills、默认模型、权限、记忆、workspace、和用户的关系。

一次 runtime session/run 只是它的当前运行态。session 可以过期、重启、迁移、被重新 spawn，但小人的身份不丢。

## 4. Product DB 是主权层

以下内容必须由产品数据库保存，不交给 OpenClaw session/channel 体系独占：

```text
users
agent_profiles
agent_instances
rooms
room_members
dm_threads
messages
runs
artifacts
memory_index
permissions
audit_events
evolution_patches
```

OpenClaw 是 runtime/harness，不是产品社交图谱的唯一来源。

## 5. OpenClaw 是第一版 runtime，但必须可替换

第一版可以用 OpenClaw 做隐藏 Main Agent、SubAgent session、worker spawn、tool/runtime 调度。

但产品层要通过 adapter 访问 runtime，避免未来接入 Codex、Claude Code、Hermes、Gemini CLI、E2B、Daytona 时推翻系统。

## 6. 单聊默认直达 SubAgent

不要让 Main Agent 每条消息都用大模型介入，否则成本高、延迟高、人格容易被主控同质化。

```text
DM: User → Product Router → Bram → User
```

Main Agent 只在这些场景介入：

```text
群聊 / Convene
结构化 Review
SubAgent 请求 worker
错误、超时、冲突、权限升级
后台反思和进化
```

## 7. 群聊是受控协作，不是自由互喷

Group/Convene 模式下，Main Agent 决定：

```text
谁应该发言
每个 SubAgent 拿到什么 context
是依次发言还是并行工作
是否需要第二轮
什么时候强制停止
最终是否生成 artifact
```

最大原则：协作过程可以复杂，但用户界面必须清爽。

## 8. 右侧审计面板默认隐藏

用户可以点击 `...` 查看后台工作，但默认不展示。审计面板展示 route、context pack、tool calls、runs、权限事件、成本和 artifact，不展示模型私密推理链。

## 9. 进化要走 Patch，不要无限自改

Main Agent 可以发现 SubAgent 的失败模式并提出修改：memory、soul、skills、tools、model、权限、harness。

但除低风险 memory/style 更新外，其他都应该生成 `EvolutionPatch`，经过审批或自动化安全规则后再应用。

## 10. 不做的事情

第一版不要做：

```text
无限数量小人
完全自治 swarm
所有 Agent 自由群聊
Main Agent 每条消息介入
默认读取所有 DM raw transcript
自动修改工具权限和代码
把 OpenClaw session 当产品 DB
```
