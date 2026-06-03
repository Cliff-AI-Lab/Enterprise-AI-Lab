---
name: 跨境物流大脑
name_en: Cross-border Logistics Brain
type: Composite Application
industry: Logistics
composed_of: [关务报关员, 包裹追踪员, 路径规划师, 外汇交易助手]
source_refs: [Legal Compliance Checker, Geographer]
apis: [AfterShip, UK Trade Tariff, ExchangeRate-API]
emoji: ✈️
---

# ✈️ 跨境物流大脑 Cross-border Logistics Brain

## Use Case
跨境电商/FBA/海外仓的运输方式选择+清关+配送+退货全流程。

## Agent Composition
```
[关务报关员] ← Legal Compliance Checker
[包裹追踪员] ← Evidence Collector
[路径规划师] ← Geographer
[外汇交易助手] ← FP&A Analyst
```

## Bound APIs
| API | Purpose |
|-----|------|
| AfterShip | 多家国际快递 |
| UK Trade Tariff | 各国税率 |
| ExchangeRate-API | 运费折算 |
| 17track | 中国邮政/专线 |

## 核心工作流
1. **方式选型**：空运/海运/铁路/专线
2. **运费比价**：DDP/DDU
3. **清关方案**：单证准备
4. **海外配送**：本地快递对接
5. **退货逆向**：回仓/弃件

## Sample Output
```
【某电商 跨境物流月报】
发往国家: 32 | 总包裹 28万
运输方式:
  - 小包专线 45% (3-10天)
  - 海外仓 32% (1-3天, FBA)
  - 国际快递 18% (3-7天 DHL)
  - 航空专线 5%
均单物流成本:
  - 美西 $4.8 | 欧洲 $5.2 | 东南亚 $3.1
时效达成:
  - 专线准时率 88%
  - 海外仓 99% (FBA加持)
关务:
  - 清关成功率 98.5%
  - 退运/弃件率 1.5%
逆向物流:
  - 欧洲退货率 12% → 合作本地仓退货
  - 美国 8% → 直接弃件 (运费不划算)
异常:
  - 红海航运成本↑30% → 迁移空运
  - 欧盟EPR 新规 注意玩具类目
```
