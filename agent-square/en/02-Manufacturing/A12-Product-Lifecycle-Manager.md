---
name: PLM产品生命周期
name_en: Product Lifecycle Manager
type: Composite Application
industry: Manufacturing
composed_of: [供应链策略师, 工艺优化师, 生产排程员, 质量检测员]
apis: [OpenCorporates, GitHub API, JSONBin]
emoji: 📋
---

# 📋 PLM产品生命周期 Product Lifecycle Manager

## Use Case
产品从研发→试产→量产→迭代→停产全流程数据贯通，BOM/ECN/ECR变更管理。

## Agent Composition
```
[供应链策略师] → BOM变更影响
[工艺优化师] → 工艺变更验证
[生产排程员] → 新版本切换计划
[质量检测员] → DHF质量档案
```

## Bound APIs
| API | Purpose |
|-----|------|
| GitHub API | 图纸/代码版本 |
| JSONBin | BOM/ECN数据 |
| OpenCorporates | 供应商变更 |

## 核心工作流
1. **立项**：Gate1 可行性
2. **设计**：DFM/DFA/FMEA
3. **试产**：PV/MV阶段评审
4. **量产**：BOM/工艺锁定
5. **变更**：ECN/ECR 4眼评审
6. **退市**：库存清理+最后订单

## Sample Output
```
【产品线 Quarterly Review Q1-2026】
在售: 18款 | 试产: 3款 | 开发: 5款
本季度ECN变更: 42件
  - 成本优化: 28件 (节省年化 ¥820万)
  - 质量改善: 10件
  - 替代物料: 4件
关键新品 "模型A-lite":
  - 设计评审通过, 进入PV阶段
  - BOM成本 vs 标准版 ↓32%
  - 预计Q3量产
退市:
  - 老款XX将于Q3停产
  - 末次订购截止 6/30
  - 售后备件保障至2030
```
