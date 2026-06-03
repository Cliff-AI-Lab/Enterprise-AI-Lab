# Hidden Admin / Evolution 推荐方案

> 讨论日期：2026-05-31。本文是基于当前 OpenClaw multi-agent 实现、三篇 clipping 和前序讨论整理的建议，供下一轮设计继续用。当前权威实现快照仍看 `00_README.md` / `../CLAUDE.md`。

> Agent-to-agent 通信、接龙房 one-shot 停止规则、Main stop/continue Phase 2 边界，见 [`14_AGENT_COMMUNICATION_PROTOCOL.md`](14_AGENT_COMMUNICATION_PROTOCOL.md)。

## 结论

可以把 OpenClaw 的隐藏 `main` 做成一个类似“系统管理员 / 控制台”的后台 Agent，但它不应该成为普通聊天成员。

更准确的定位：

```text
main = Hidden Admin / Supervisor / Attention OS
```

它的目的不是替 Sarah/Alex/Kai 说话，而是治理这些 SubAgent 的注意力、上下文、权限、状态、反馈和进化。

用户看到的是 AI 小人；系统内部真正治理的是：

```text
Attention Scope
Context Scope
Tool Scope
State Scope
Environment Scope
Feedback Scope
Memory Scope
```

## 三篇文章的吸收

### Prompts, Now Programmable

可参考点：prompt 可以变成版本化、可复用、可执行的流程资产。

在本项目里的对应关系：

```text
IDENTITY.md  = 这个 agent 是谁
SOUL.md      = 这个 agent 为什么存在、价值观、边界、语气
AGENTS.md    = 和其他 agent 如何协作、职责边界
TOOLS.md     = 工具使用偏好和限制
HEARTBEAT.md = 定时醒来时做什么
skills/*.md  = 可复用能力 / Prompt Flow / 工作流
```

不要把流程塞进 `SOUL.md`。`SOUL.md` 是人格内核；Prompt Flow 应该放在 `skills/` 或 `HEARTBEAT.md` 里。

### 多 Agent 的本质不是分工，而是注意力治理

这篇对架构影响最大。

不要把 Sarah/Alex/Kai/Main 只理解成“角色”。如果它们看到同样上下文、拥有同样工具、修改同样状态、没有独立反馈，那只是多 prompt，不是多 agent。

真正的 Agent 边界应该由这些东西定义：

```text
Agent = Identity + Soul + Context + Tools + State + Environment + Feedback + Memory
```

所以 Main/Admin 的核心职责不是“分配员工”，而是：

```text
这一步谁应该看哪些上下文？
哪些信息不该给它？
哪些工具可以开？
允许它改什么状态？
结果如何验证？
失败如何回滚？
哪些记忆可以沉淀？
```

### 4-agent team overnight pipeline

可参考点不是“Planner/Coder/Tester/Reviewer 四个角色”，而是：

```text
窄上下文
阶段化 handoff
每阶段权限不同
失败即停
最后只出 verdict
不自动 merge
```

文章里的 `.pipeline/spec.md`、`.pipeline/changes.md`、`.pipeline/test-results.md`、`.pipeline/review.md` 可以转成我们自己的 artifacts / audit_events / context_pack_snapshots。

不建议照搬成 4 个可见 SubAgent。更适合做成 `main` 的 workflow skill。

## 推荐架构

当前 OpenClaw 结构保持不变：

```text
main   = hidden configured agent
sarah  = visible configured agent
alex   = visible configured agent
kai    = visible configured agent
maruko = visible configured agent
```

新增概念：

```text
Admin Console Channel
  - 平时不可见
  - 不进入普通 room list
  - 可从本地 UI 的隐藏入口触发
  - 后续可接 Telegram bot，但必须先经过我们的后端

Main/Admin Workflows
  - repo-guardian
  - agent-evolution
  - persona-generator
```

关键原则：

```text
不要让 Telegram 直接接 OpenClaw channel
不要让 main 默认读取所有私聊 raw transcript
不要让 main 静默改代码、权限、openclaw.json
不要让 workflow 输出直接进入用户聊天流
```

Telegram 以后可以作为 admin inbox/outbox，但应接到我们的后端，由后端写 DB、做权限检查、生成 audit，再调用 OpenClaw `main`。

## 上下文增长防线

OpenClaw 的 configured agent 是 per-agent workspace 隔离的。调用 `openclaw/sarah` 时，默认只加载 Sarah 自己的 workspace prompt，不会自动把 Alex/Kai/Maruko/Main 的 `SOUL.md` 全部塞进 Sarah 的上下文。

OpenClaw 的临时 `sessions_spawn` sub-agent 更小，只加载 `AGENTS.md` / `TOOLS.md`，不加载 `SOUL.md` / `IDENTITY.md` / `USER.md`。这类 sub-agent 应作为 Worker Run，而不是产品里的可见 SubAgent。

真正需要防的是我们自己的编排层把上下文撑爆：

```text
风险 1: main 的 SOUL/AGENTS 里手写所有 SubAgent 的详细人格全文
风险 2: 群聊 ContextPack 把整个 room history 发给所有人
风险 3: evolution loop 默认读取全部 DM raw transcript
风险 4: agentToAgent 调用时转发完整上下文
风险 5: 每个 agent allowlist 过多 skills
风险 6: memory_search 没有 top-k / relevance 限制
```

硬规则：

```text
Main/Admin 只常驻轻量 agent registry:
  - id
  - name
  - role
  - capabilities
  - tool/permission summary
  - last health summary

不要常驻:
  - 完整 SOUL.md
  - 完整 IDENTITY.md
  - 完整 DM transcript
  - 全部 memory chunks
```

当 SubAgent 数量增加时，流程应该是：

```text
1. 用 lightweight registry 选 1-3 个候选
2. 只读取候选的详细 persona / recent summary
3. 为每个目标 agent 生成专属 ContextPack
4. ContextPack 引用 artifact id / summary，少传 raw text
5. audit 记录 redactions：哪些内容没传、为什么没传
```

群聊 ContextPack 默认只包含：

```text
room_goal
your_task_this_round
relevant inputs
last N messages summary
artifact refs
permission snapshot
redactions
```

不要把所有 SubAgent 的全部人格和历史拼成一个“大脑”。系统能力来自按需调度注意力，不来自把所有信息塞进同一个上下文。

## Workflow 1: Repo Guardian

目的：每天扫 repo 状态、diff、测试结果、遗留问题，生成可审计报告和少量优化建议。

边界建议：

```text
Attention Scope:
  git status / git diff / recent commits / ISSUE.md / TODO / failing checks

Context Scope:
  仅读 repo 相关文件；默认不读用户私聊

Tool Scope:
  read/search/git diff/test/build；写代码默认禁用

State Scope:
  只能写 reports/YYYY-MM-DD.md、audit_events、pending patch

Environment Scope:
  本地 repo；测试命令按项目已有脚本；长任务有 timeout

Feedback Scope:
  lint/typecheck/test/build 结果，不用“模型觉得可以”替代验证

Memory Scope:
  把重复问题沉淀到 report 或 evolution.md，不直接污染 SOUL.md
```

推荐最小 Prompt Flow：

```text
A: BEGIN
B: Read git status, git diff, recent commits, ISSUE.md
C: Detect changed surfaces and likely risk areas
D: Run the narrowest relevant checks
E: Summarize failures, regressions, skipped checks, and uncertainty
F: Propose at most 3 improvements
G: Classify risk: low / medium / high
H: Write report and audit event
I: END

A -> B -> C -> D -> E -> F -> G -> H -> I
```

MVP 默认不自动改代码。最多生成 proposed patch。

## Workflow 2: Agent Evolution

目的：观察 SubAgent 的人设、能力、工具使用和失败模式，提出可审计的进化建议。

边界建议：

```text
Attention Scope:
  用户纠正、重复失败、工具失败、跑偏、被其他 agent 反驳、用户重写

Context Scope:
  优先读摘要和 audit；默认不读全部 DM raw transcript

Tool Scope:
  read messages/audit/reports/persona files；默认只生成 patch

State Scope:
  可写 pending evolution.md；自动改 SOUL/TOOLS/skills 需审批

Environment Scope:
  persona workspace；OpenClaw 热重载不工作，应用后需 gateway restart

Feedback Scope:
  验证脚本、真实对话 case、用户反馈

Memory Scope:
  低风险事实进 memory；中高风险人格/权限变更进 pending patch
```

推荐输出格式沿用 `temp_design.md §5.5.5`：

```markdown
## 2026-05-31 22:00 [pending-review]
**Proposed by:** main/admin reflector
**Target:** sarah
**Target file:** SOUL.md
**Quality Signal:** user_correction_repeated x3
**Reason:** ...
**Evidence:** ...
**Patch:** ...
**Risk:** low | medium | high
**Rollback:** ...
**Status:** pending-review
```

MVP 全人审。后续最多允许 low-risk memory/style note 自动应用；权限、工具、模型、代码、OpenClaw config 都必须审批。

## Workflow 3: Persona Generator

目的：通过 Main/Admin 生成新 SubAgent，例如“小说家”。

正确路径：

```text
1. main 先生成 persona proposal
2. 用户确认 name / role / visibility / skills / model
3. 生成 personas/<id>/{IDENTITY,SOUL,USER,AGENTS,TOOLS,HEARTBEAT}.md
4. 修改 openclaw.json agents.list
5. 同步 ~/.openclaw/openclaw.json
6. 重启 OpenClaw Gateway
7. agentSync 同步 DB，前端出现新 DM
```

风险边界：

```text
新增普通 persona = medium risk
新增 skills = medium risk
新增工具权限 / shell / file write = high risk
修改 openclaw.json = high risk
```

## Main/Admin 的 Soul 建议

`personas/main/SOUL.md` 应从默认模板改成明确的后台管理员人格。

它应该强调：

```text
你是隐藏系统管理员，不是聊天角色。
你的工作是改善 SubAgent 的长期表现，而不是替它们发言。
你优先生成结构化决策、audit、patch、report。
你默认不读取所有私聊原文。
你默认不静默修改代码、权限、OpenClaw config。
你提出小步、可验证、可回滚的进化建议。
```

`personas/main/IDENTITY.md` 应明确：

```text
Name: Console / Admin / Supervisor 之一
Role: Hidden system administrator
Visible: false
```

## 落地顺序

### Step 1: Main/Admin persona 定型

改 `personas/main/IDENTITY.md`、`SOUL.md`、`AGENTS.md`、`TOOLS.md`。

目标：让 main 明确自己是隐藏管理员，而不是默认 OpenClaw assistant。

### Step 2: 本地 admin endpoint

新增一个后端隐藏入口，例如：

```text
POST /api/admin/main/messages
```

这个入口不进入普通 room list，不生成普通 agent bubble。输出写 audit / report / pending patch。

### Step 3: Repo Guardian 手动触发

先做手动按钮或命令，不做 cron。

输出：

```text
reports/YYYY-MM-DD-repo-guardian.md
audit_events
最多 3 个建议
```

### Step 4: Agent Evolution 手动触发

扫描 messages / reports / persona files，生成 pending `evolution.md`，不自动应用。

### Step 5: Cron

手动稳定后再加定时：

```text
Repo Guardian: 每天一次
Agent Evolution: 每周一次，或每天轻扫每周深扫
```

### Step 6: Telegram admin inbox

Telegram 不直连 OpenClaw channel。先接我们的后端：

```text
Telegram Bot -> Backend Admin API -> Permission/Audit -> OpenClaw main
```

用途：

```text
用户主动提出改进需求
Main 定期推送 pending report / pending patch
用户批准或拒绝
```

## 不做

MVP 不做：

```text
自动长期自改代码
自动 merge / push
默认读取所有 DM raw transcript
直接开放 OpenClaw Telegram channel 给 main
无限循环 Ralph Loop
固定 4-agent 小队作为产品核心
每次普通 DM 都让 main 介入
```

## 一句话原则

```text
SOUL.md 决定 agent 想成为什么；
Prompt Flow 决定 agent 怎么工作；
Permission/Audit/Feedback 决定它能不能可靠地工作。
```
