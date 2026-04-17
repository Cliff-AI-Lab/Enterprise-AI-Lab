---
name: 碳金融交易
name_en: Carbon Finance Trading
type: Composite Application
industry: Finance
apis: [Carbon Interface, Climatiq, Alpha Vantage]
emoji: 🌍
---

# 🌍 碳金融交易 Carbon Finance Trading

## Use Case
碳配额/CCER/绿证交易员的做市+自营+客户代理。

## Core Capabilities
- 多市场行情聚合 (CEA/EU-ETS/CCA)
- 做市报价
- 跨市场套利
- 碳期货+现货组合

## Bound APIs
| API | Purpose |
|-----|------|
| Carbon Interface | 排放核算 |
| Climatiq | 碳因子 |
| Alpha Vantage | EUA期货 |

## Sample Output
```
【碳金融交易台 日报 2026-04-17】
EUA: €72.5/吨 (↑1.2%)
CEA: ¥88/吨 (↑2.1%)
CCER: ¥68/吨
跨市场溢价: EU vs CN 折合 ¥485/吨 差价
交易:
  - 做市挂单 1200手双边
  - 套利盈利 ¥18万
  - 客户代理成交 5笔 合计¥3,800万
持仓: 净多 ¥500万 市值
```
