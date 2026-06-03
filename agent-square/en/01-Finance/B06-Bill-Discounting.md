---
name: 票据贴现
name_en: Bill Discounting
type: Composite Application
industry: Finance
apis: [OpenCorporates, Treasury.gov, ExchangeRate-API]
emoji: 📜
---

# 📜 票据贴现 Bill Discounting

## Use Case
银行/票据中介的商票/银票贴现+转贴现+买断式定价。

## Core Capabilities
- 承兑人资质核查
- 票据真伪鉴别
- 贴现率报价
- 资金匹配

## Bound APIs
| API | Purpose |
|-----|------|
| OpenCorporates | 承兑人查询 |
| Treasury.gov | 基准利率 |

## Sample Output
```
【票据中心 日报】
贴现量: ¥18.5亿 | 笔数 2,400
平均期限 120天
承兑分布:
  - 国股银票 ¥8.2亿 (价低) 2.35%
  - 城商+农商 ¥6.2亿 2.65%
  - 优质商票 (AAA国企) ¥3.1亿 3.2%
  - 一般商票 ¥1亿 4.5%
风控:
  - 拒收疑似假票 12张
  - 出账前双人复核
资金成本: 2.1% | 毛利率 0.8-1.2%
```
