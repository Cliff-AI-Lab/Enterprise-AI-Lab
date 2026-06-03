> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# 产品输出定义

本文定义系统最终“产出什么”。这里的输出包括用户在聊天界面看到的内容，也包括右侧审计面板、后台 artifact、权限提示和进化 patch。

## 输出总览

| 输出 | 是否用户默认可见 | 来源 | 用途 |
|---|---:|---|---|
| Chat Message | 是 | 单个 SubAgent | 日常单聊回复 |
| Group Message | 是 | 被 Main 调度的 SubAgent | 群聊中某个小人的发言 |
| Summary Card | 是 | Main Agent 生成，但不人格化 | 汇总协作结果 |
| Review Artifact | 是 | 多 Agent + Main 合并 | 代码/设计/研究 review 产物 |
| Task Artifact | 是/可选 | SubAgent 或 Worker Run | 文档、patch、报告、图、清单 |
| Permission Prompt | 是 | Permission Gateway | 请求用户批准高风险操作 |
| Status Event | 是/轻量 | Runtime/Queue | online/thinking/working/waiting/offline |
| Audit Trace | 默认隐藏 | Runtime + Product | 右侧 `...` 面板查看 |
| ContextPack Snapshot | 默认隐藏 | Main/Router | 审计时查看某轮给了谁什么上下文 |
| EvolutionPatch | 后台/管理可见 | Main Supervisor | 修改小人能力、记忆或配置的提案 |

## 1. Chat Message

单聊中 SubAgent 的普通回复。

要求：

```text
sender = SubAgent
visible = true
conversation_type = dm
main_agent_visible = false
```

示例：

```text
Bram: 这个实现我建议先砍到两个接口：createRoom 和 routeTurn。不要先做复杂权限，先把消息流跑通。
```

## 2. Group Message

群聊中某个 SubAgent 的发言。即使是 Main Agent 调度产生，也必须显示为具体小人的消息。

要求：

```text
sender = SubAgent
visible = true
conversation_type = room
source_run_id = group_round_run
```

示例：

```text
Luna: 这个界面的信息层级是对的，但 Convene 和 Review 的视觉权重太接近，用户可能不知道当前处于哪种模式。
```

## 3. Summary Card

Main Agent 可以生成总结，但不能以人格说话。Summary Card 是系统产物，不是 Main Agent 发言。

要求：

```text
sender_type = system_card
card_type = summary
main_agent_name_hidden = true
```

推荐格式：

```markdown
### Summary

**必须处理**
1. xxx
2. xxx

**建议处理**
1. xxx

**下一步**
- 选择 A / B / C
```

## 4. Review Artifact

Review 模式的核心输出。它不是聊天消息，而是一个可保存、可引用、可再次 review 的 artifact。

适用场景：

```text
代码 review
产品方案 review
UI review
研究证据 review
PRD review
写作 review
```

推荐结构：

```markdown
# Review Artifact

## Verdict
通过 / 条件通过 / 不通过

## Must Fix
- 问题
- 影响
- 建议改法
- 负责人或推荐 SubAgent

## Should Fix
...

## Evidence
- 文件、截图、引用、测试结果

## Agent Notes
- Bram: ...
- Luna: ...
- Echo: ...

## Next Action
...
```

## 5. Task Artifact

SubAgent 或 Worker Run 生成的工作产物。例如：

```text
research_report.md
implementation_plan.md
ui_critique.md
patch.diff
test_result.txt
source_map.md
```

Task Artifact 必须可追溯到：

```text
source_run_id
creator_agent_id
input_context_pack_id
tool_calls
permission_snapshot
created_at
```

## 6. Permission Prompt

任何高风险操作必须输出权限提示，而不是静默执行。

触发例子：

```text
写文件
执行 shell
访问 GitHub token
读取私聊内容
把一个 DM 摘要分享到群里
调用外部付费 API
修改 SubAgent 的 tools/soul/model
```

推荐格式：

```text
Bram 想读取 repo: /apps/web 的 12 个文件用于 review。
范围：只读
有效期：本次 run
风险：低
[允许一次] [允许本房间] [拒绝]
```

## 7. Status Event

小人状态不是简单 presence，而是产品层状态。

```text
online   可响应
thinking 正在生成回复
working  正在跑工具/研究/代码
waiting  等用户批准
away     降级或低优先级
offline  禁用/不可用
```

状态必须来自 queue、run、provider health、permission state，而不是只看进程是否活着。

## 8. Audit Trace

右侧 `...` 面板打开后展示。

包含：

```text
routing decision
selected agents
context packs
tool calls
worker runs
permission events
artifacts
cost / latency
errors / retries
```

不包含：

```text
模型私密推理链
未授权私聊 raw transcript
凭证明文
系统 prompt 全文
```

## 9. ContextPack Snapshot

每轮调度给某个 SubAgent 的上下文快照。

它是审计关键：用户需要知道系统“把什么告诉了谁”。

最低字段：

```ts
type ContextPackSnapshot = {
  id: string
  roomId?: string
  targetAgentId: string
  purpose: 'dm_turn' | 'group_round' | 'review' | 'worker'
  includedMessages: MessageSummary[]
  includedArtifacts: ArtifactSummary[]
  includedMemories: MemorySnippet[]
  excludedPrivateItems: RedactionNotice[]
  permissionSnapshotId: string
}
```

## 10. EvolutionPatch

Main Agent 后台提出的“让小人变好”的修改建议。

推荐格式：

```markdown
# Evolution Patch

target: Bram
patch_type: skill_update
risk: medium
requires_approval: true

## Evidence
最近 6 次 review 中有 3 次没有明确给出实现风险等级。

## Proposed Change
- 给 Bram 增加 risk_ranking_checklist.md
- 在 Bram 的 AGENTS.md 中加入 “每次 review 必须输出 risk: low/medium/high”

## Rollback
删除新增 checklist，并恢复 AGENTS.md 上一版。
```
