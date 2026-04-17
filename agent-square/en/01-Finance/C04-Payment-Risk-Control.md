---
name: 第三方支付风控
name_en: Payment Risk Control
type: Composite Application
industry: Finance
apis: [HIBP, OpenSanctions, VirusTotal]
emoji: 💳
---

# 💳 第三方支付风控

## Use Case
支付宝/Stripe类支付机构的交易反欺诈+洗钱监测。

## Core Capabilities
- 实时交易评分
- 商户准入+监测
- 卡/账户黑名单
- 套现识别

## Sample Output
```
【支付日报】
交易笔数: 18亿 | 金额 ¥82亿
拦截:
  - 疑似欺诈交易 120万笔 (拦截率99.3%)
  - 洗钱可疑 4,200笔
  - 套现商户 停用 82家
资损率: 0.002bp (同业0.01bp)
```
