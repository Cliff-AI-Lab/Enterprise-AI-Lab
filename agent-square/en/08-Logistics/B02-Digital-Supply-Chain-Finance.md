---
name: 数字供应链金融
name_en: Digital Supply Chain Finance
type: Composite Application
industry: Logistics
apis: [OpenCorporates, AfterShip, ExchangeRate-API]
emoji: 🔗
---

# 🔗 数字供应链金融 Digital Supply Chain Finance

## Use Case
核心企业+物流+金融三方融合: 基于物流数据做动产质押融资。

## Core Capabilities
- 在途/在库货权监管
- 自动质押+放款
- 风险监控
- 回款闭环

## Bound APIs
| API | Purpose |
|-----|------|
| AfterShip | 在途确权 |
| OpenCorporates | 主体合规 |
| ExchangeRate-API | 跨境 |

## Sample Output
```
【物流金融平台 月报】
在贷: ¥8.2亿 | 客户 186家
融资模式:
  - 应收账款保理 42%
  - 动产质押 (在库) 28%
  - 在途货物监管 18%
  - 订单融资 12%
利率: LPR+150-300BP
不良率: 0.45% (同业平均1.2%)
物流联动:
  - 全部押品GPS+温湿度监控
  - 货权异动即时预警
  - 风险处置: 12小时控货
回款: 自动清分 100%准确
```
