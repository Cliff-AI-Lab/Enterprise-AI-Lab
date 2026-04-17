---
name: MCP-Server运营
name_en: MCP Server Operations
type: 组合应用
industry: 科技
composed_of: [API集成工程师, 云资源管理员, AI模型评测师]
source_refs: [MCP Builder(specialized), Backend Architect, LSP/Index Engineer, Software Architect]
apis: [GitHub API, HuggingFace, Anthropic API]
emoji: 🔌
---

# 🔌 MCP-Server运营 MCP Server Operations

## 应用场景
为Claude/Cursor等客户端提供MCP(Model Context Protocol) Servers的开发/托管/运营。

## Agent组合
```
[MCP Builder] ← specialized
[API集成工程师] ← Backend Architect
[云资源管理员] ← Infrastructure Maintainer
[LSP/Index Engineer] ← specialized
```

## 绑定API
| API | 用途 |
|-----|------|
| GitHub API | Server托管 |
| Anthropic API | Claude集成 |
| 各业务API | 作为工具封装 |

## 核心工作流
1. **需求采集**：开发者高频诉求
2. **Server开发**：工具/资源/提示
3. **发布分发**：Hub/NPM
4. **托管运维**：弹性+监控
5. **生态运营**：教程+案例

## 典型输出
```
【MCP Hub 月度运营】
已发布Servers: 48 (官方12 + 社区36)
日活: 2.4万开发者
Top10:
  1. GitHub MCP (代码管理)
  2. Slack MCP
  3. Notion MCP
  4. Filesystem MCP
  5. PostgreSQL MCP
  ...
本月新增:
  - 飞书/企微 MCP (国内需求)
  - Figma MCP (设计师)
  - YouTube Data MCP
使用场景:
  - IDE Agent (Claude Code/Cursor) 占68%
  - Desktop App 22%
  - 自定义 10%
增长:
  - 下载量 +45% MoM
  - 社区贡献PR 120+
  - Discord 8,200+人
```
