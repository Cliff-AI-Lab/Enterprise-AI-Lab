---
name: 多式联运规划
name_en: Multimodal Transport Planner
type: Composite Application
industry: Logistics
composed_of: [路径规划师, 关务报关员, 包裹追踪员, 外汇交易助手]
source_refs: [Geographer, Legal Compliance Checker]
apis: [OpenRouteService, UK Trade Tariff, ExchangeRate-API, AfterShip]
emoji: 🚂
---

# 🚂 多式联运规划 Multimodal Transport Planner

## Use Case
中欧班列/铁海联运/陆空联运等跨运输方式的最优组合规划。

## Agent Composition
```
[路径规划师] ← Geographer
[关务报关员] ← Legal Compliance Checker
[包裹追踪员] ← Evidence Collector
[外汇交易助手] ← FP&A Analyst
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenRouteService | 路径规划 |
| UK Trade Tariff | 关税 |
| AfterShip | 多段追踪 |
| ExchangeRate-API | 跨币种 |

## 核心工作流
1. **需求分析**：货量+时效+成本
2. **组合建模**：公+铁+海+空
3. **节点调度**：各环节衔接
4. **报关办理**：各关境
5. **一票到底**：统一单证

## Sample Output
```
【中欧班列 + 欧内公铁 联运方案】
起讫: 义乌 → 巴黎 | 货物 20*40HQ 电子产品
方案A (全海运):
  - 时效 42天
  - 成本 $62K
  - 准时率 85%
方案B (中欧班列+欧内公路):
  - 时效 18天 ✅ (快24天)
  - 成本 $78K
  - 准时率 92%
方案C (班列+海运混合):
  - 波兰马拉舍维奇 再经汉堡海运
  - 22天, $70K
推荐: 方案B
  - 对时效敏感的电子产品
  - 可节省资金占用 $65万(货值)
  - RCEP/一带一路政策支持
碳排比较: 班列仅为海运1/7
```
