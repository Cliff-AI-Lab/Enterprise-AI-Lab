---
name: RPA业务流程
name_en: RPA Process Automation
type: Composite Application
industry: Technology
composed_of: [DevOps自动化师, 文档生成专家, 财务记账员, 应付账款专员]
source_refs: [Workflow Architect, Automation Governance Architect]
apis: [GitHub API, PDFMonkey, Invoice Generator]
emoji: 🤖
---

# 🤖 RPA业务流程 RPA Process Automation

## Use Case
财务/HR/采购/客服等后台高频重复流程自动化, 替代人工点击。

## Agent Composition
```
[DevOps自动化师] ← DevOps Automator
[文档生成专家] ← Document Generator
[Workflow Architect] ← specialized
[Automation Governance Architect] ← specialized
```

## Bound APIs
| API | Purpose |
|-----|------|
| PDFMonkey | 报表生成 |
| Invoice Generator | 发票 |
| GitHub API | 版本管理流程 |

## 核心工作流
1. **流程挖掘**：筛选高ROI
2. **流程建模**：BPMN
3. **机器人开发**：RPA脚本
4. **治理**：权限/审计/应急
5. **监控**：异常告警

## Sample Output
```
【RPA季度运营报告】
在线机器人: 218个 | 流程: 82项
节省人工:
  - 本季度 18,400 工时
  - 相当 9.2 FTE
  - 年化节省 ¥220万
Top机器人:
  1. 发票验真+入账 日处理2,400张
  2. HR入离职自动化 月200+
  3. 对账单自动生成 100+客户
  4. 供应商付款单 日1,000+
  5. 工单填报 日800+
异常:
  - 2次流程失败 (系统升级导致)
  - 已更新适配脚本
治理:
  - 新增流程4个 (通过风险评审)
  - 下线无效流程3个
  - 全部机器人有责任人+日志
```
