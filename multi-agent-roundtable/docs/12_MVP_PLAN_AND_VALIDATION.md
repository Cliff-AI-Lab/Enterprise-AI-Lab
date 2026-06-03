> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# MVP 路线与验证计划

## MVP 目标

先证明一个产品闭环：

```text
用户能和多个小人单聊；
能把小人拉进群；
隐藏 Main Agent 能调度群聊和 Review；
右侧审计能展示后台过程；
小人身份、记忆、权限、产物由产品 DB 管；
OpenClaw 作为 runtime 能承载第一版。
```

## MVP 不做

```text
无限小人 marketplace
完全自治 swarm
复杂社交关系图
自动长期自改代码
全量多平台接入
企业级权限矩阵
全自动 RL
```

## 阶段 0：技术验证

目标：半天到两天内验证 OpenClaw/runtime 可行性。

必须验证：

```text
1. Main 能否拉起/恢复多个 SubAgent-like sessions
2. 每个 SubAgent 能否拥有独立 model/tools/skills/workspace/memory
3. session 丢失后能否靠产品 DB + workspace 恢复身份
4. Main 能否把 A 的 report 传给 B
5. Main 能否并行调度多个 SubAgent 并合并结果
6. 是否能限制工具权限和 sandbox
7. 是否能记录 route/context/tool/run 的审计事件
8. 外部 harness 是否绕过 sandbox，需要单独 permission gateway
```

最小 demo：

```text
Bram: 工程小人
Luna: 设计小人
Main: 隐藏 coordinator
任务：用户上传一个简单 UI/代码片段，点击 Review
结果：Bram + Luna 各自输出，Main 生成 Summary Card
审计：能看到 route、context、run、tool call
```

## 阶段 1：单聊 MVP

功能：

```text
左侧 contacts
Bram/Nova/Atlas/Iris 4 个小人
DM direct routing
消息存档
thinking/working/waiting 状态
基础 memory note
右侧 audit: run trace
```

验收：

```text
用户能连续和 Bram 聊 10 轮
Bram 能记住用户明确要求记住的偏好
刷新页面后上下文可恢复
Main 不介入普通 DM
```

## 阶段 2：Convene MVP

功能：

```text
创建 room
添加多个 SubAgent
@mention route
selected speakers
round robin
parallel then merge
summary card
```

验收：

```text
用户创建“Interface Review” room
拉 Bram + Luna + Iris
提一个开放问题
系统最多让 3 个小人发言
最后给 Summary Card
Main 不出现在消息成员里
右侧审计能看到 Main 的选择原因
```

## 阶段 3：Review MVP

功能：

```text
Review tab
固定 review protocol
Bram engineering finding
Luna UI finding
Echo evidence finding 可选
Main merge artifact
Must Fix / Should Fix / Optional
```

验收：

```text
用户提交代码 diff / 设计截图 / 文案
系统产出 Review Artifact
每个 finding 可追溯到 SubAgent 和 run
超过 2 轮自动停止
```

## 阶段 4：权限与审计

功能：

```text
Permission Prompt
file read/write scope
shell exec approval
private context sharing approval
right-side audit panel
trace events
kill switch
```

验收：

```text
Bram 请求读文件时用户能批准/拒绝
Main 不能默认把 DM 私聊发到 group
审计面板展示 context pack 和 redaction
用户可取消 run
```

## 阶段 5：Evolution Loop

功能：

```text
低风险 memory update
failure pattern detection
EvolutionPatch 生成
审批/拒绝/rollback
```

验收：

```text
Main 能发现 Bram 的重复失败模式
生成一个 skill_update patch
用户批准后应用
下一次 review 输出格式改善
```

## MVP 成功指标

```text
单聊首包延迟可接受
群聊不超过 2 轮默认收敛
Review Artifact 可直接行动
用户能理解每个小人的能力
用户信任审计面板
没有 Main Agent 露面破坏体验
权限提示不打扰但关键时出现
```

## 首批小人建议

```text
Bram  Builder / Engineer
Luna  Designer
Echo  Researcher
Iris  Writer
Atlas Planner
```

先做 4 个就够：Bram、Luna、Echo、Iris。Atlas 可以第二批。

## 最短实现路径

```text
1. 先实现 Product DB + DM direct
2. 接 OpenClaw adapter
3. 做 4 个 SubAgent profile
4. 做 Hidden Main 的 Convene 协议
5. 做 Summary Card
6. 做 Review Artifact
7. 做右侧 Audit Panel
8. 做 Permission Gateway
9. 最后做 EvolutionPatch
```

## 最大风险

```text
OpenClaw raw sub-agent 不适合长期人格
Main Agent 介入太多导致成本/延迟爆炸
权限边界不清导致信任问题
群聊展示太多内部过程导致体验像 debug console
外部 harness 绕过 sandbox
```

## 对应缓解

```text
产品层 SubAgent 抽象独立于 raw runtime session
DM 默认直达
Main 只在 Convene/Review/异常/进化时介入
审计默认隐藏
Permission Gateway 独立于 OpenClaw
所有高风险进化走 Patch 审批
```
