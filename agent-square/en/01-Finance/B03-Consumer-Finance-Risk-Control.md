---
name: 消费金融风控
name_en: Consumer Finance Risk Control
type: Composite Application
industry: Finance
apis: [OpenSanctions, HIBP, Alpha Vantage]
emoji: 🎯
---

# 🎯 消费金融风控 Consumer Finance Risk Control

## Use Case
分期/信用卡/助贷平台的欺诈识别+资信评估+反撸口子。

## Core Capabilities
- 实时反欺诈评分
- 黑产设备指纹识别
- 薅羊毛聚集识别
- 多头借贷筛查

## Bound APIs
| API | Purpose |
|-----|------|
| HIBP | 手机/邮箱泄露库 |
| OpenSanctions | 黑名单 |
| Alpha Vantage | 宏观利率 |

## Sample Output
```
【消费金融风控 月报】
申请: 68万 | 通过 42万 (62%)
反欺诈拦截: 2.4万 (3.5%)
  - 设备指纹异常 42%
  - 多头借贷>6家 28%
  - 黑名单命中 15%
  - 羊毛党聚集 15%
资产质量:
  - M1逾期率 2.2% (行业3.5%)
  - M3+ 0.8%
ROE: 22%
```
