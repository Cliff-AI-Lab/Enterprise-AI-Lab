---
name: REITs分析师
name_en: REITs Analyst
type: Composite Application
industry: Finance
apis: [SEC EDGAR, Alpha Vantage]
emoji: 🏢
---

# 🏢 REITs分析师

## Use Case
不动产投资信托REITs的股息率、出租率、NAV分析。

## 核心指标
- 股息率 (DY)、FFO/AFFO
- 出租率、NOI增长率
- P/NAV、隐含资本化率
- 租户集中度

## Bound APIs
- **SEC EDGAR**: REITs季报
- **Alpha Vantage**: 股价

## Sample Output
```
【美国零售REITs Q1扫描】
组合: Simon Property / Realty Income / VICI
平均DY: 5.8% | FFO增长 3.2% | 出租率 95%
推荐: Realty Income (稳健+月付)
风险: 线下零售冲击持续
```
