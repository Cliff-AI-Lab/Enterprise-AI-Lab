> ⚠️ **[STALE — 2026-05-29]** 这是基于 "Main spawn Bram/Nova/Atlas/Iris" 的早期 GPT 设计，第 9 轮已被原生 multi-agent 模型推翻（visible subagent = OpenClaw `agents.list[]` 各一项）。**当前实现快照看 [`00_README.md`](00_README.md)** / [`../CLAUDE.md`](../CLAUDE.md)；历史决策链见 [`../temp_design.md`](../temp_design.md)。

---

# UI 与运行模式

## UI 心智模型

界面看起来像 Telegram/Slack：

```text
左侧：聊天、群组、小人联系人
中间：当前 DM 或 room
顶部：Chat / Convene / Review
右侧 ...：隐藏审计和后台工作
```

用户不需要理解 runtime、OpenClaw、spawn、worker、session。他只需要理解：

```text
我可以和 Bram 单聊。
我可以把 Bram、Luna、Echo 拉进一个 room。
我可以点 Convene 让他们协作。
我可以点 Review 让他们按固定协议产出评审。
我可以点 ... 查看幕后做了什么。
```

## Chat 模式

Chat 是最低成本、最低延迟、人格最稳定的模式。

```text
User → Product Router → SubAgent → User
```

Main Agent 默认不介入。

适用场景：

```text
和 Bram 讨论实现
和 Iris 改文案
和 Luna 看设计方向
和 Echo 问资料
```

UI 输出：

```text
普通小人消息
少量状态提示：thinking / working / waiting
必要时 permission prompt
```

## Convene 模式

Convene 是临时拉群/协作模式。

触发方式：

```text
用户点 Convene
用户创建 group
用户在 room 中 @ 多个 SubAgent
用户输入明显需要多 Agent 的请求
```

Main Agent 在后台介入：

```text
选择参与者
选择协作协议
分发不同 ContextPack
控制轮数
合并重复内容
生成 Summary Card
```

UI 输出：

```text
多个 SubAgent 的群聊消息
可选 Summary Card
可选 Artifact
```

Convene 不是让 Agent 自由聊天，而是让 Main Agent 控制一场协作。

## Review 模式

Review 是结构化工作流，不是随意群聊。

适用场景：

```text
代码 review
设计 review
PRD review
研究 review
文章 review
架构 review
```

推荐固定流程：

```text
1. Main 识别 review 类型
2. 选择 SubAgent 队伍
3. 分配角色和 checklist
4. 每个 SubAgent 独立输出 findings
5. 如果冲突，最多一轮 debate
6. Main 生成 Review Artifact
7. UI 展示 artifact + 精简群聊摘要
```

Review 模式必须有结束条件：

```text
最多 2 轮
必须输出 verdict
必须输出 must-fix / should-fix / next action
```

## 右侧 `...` 审计面板

默认隐藏。打开后展示：

```text
Route Decision
Context Packs
SubAgent Runs
Worker Runs
Tool Calls
Permission Events
Artifacts
Cost / Latency
Errors / Retries
Evolution Notes
```

不要展示：

```text
模型完整隐藏推理链
未授权私聊原文
token/secret
系统 prompt 全文
```

## Pin 顶部

Pin 是产品层功能，不是 runtime 功能。

可 Pin：

```text
重要 room
重要 SubAgent DM
重要 artifact
当前 review
长期项目 context
```

Pin 的目标是让用户快速回到持续项目，而不是让 runtime session 永久存活。

## 小人状态展示

UI 状态建议：

```text
绿色点：online
蓝色 spinner：thinking
工具图标：working
黄色点：waiting approval
灰色点：away/offline
```

状态文案要解释用户关心的事实：

```text
Bram 正在读代码
Echo 正在查证据
Luna 等你批准读取截图
Atlas 暂时离线，模型不可用
```

不要展示内部实现：

```text
runtime session key expired
childSessionKey missing
provider 429
```

这些放审计面板。
