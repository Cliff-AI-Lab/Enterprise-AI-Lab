---
name: IPO询价分析师
name_en: IPO Pricing Analyst
type: Composite Application
industry: Finance
composed_of: [股票分析师, 投资组合管理师, 新闻聚合编辑]
apis: [SEC EDGAR, Alpha Vantage, NewsAPI]
emoji: 🆕
---

# 🆕 IPO询价分析师 IPO Pricing Analyst

## Use Case
为机构询价报价提供定价建议，对标可比公司+市场情绪+基石投资者。

## Agent Composition
```
[股票分析师] → 公司基本面+可比公司
[投资组合管理师] → 申购优先级
[新闻聚合编辑] → 市场情绪/认购传言
```

## Bound APIs
| API | Purpose |
|-----|------|
| SEC EDGAR/HKEX | 招股书 |
| Alpha Vantage | 可比公司估值 |
| NewsAPI | 路演报道 |

## 核心工作流
1. **招股书解读**：业务/财务/募投
2. **估值区间**：PE/PS/PEG/DCF
3. **可比公司**：3-5家同行
4. **申购建议**：破发概率
5. **分配建议**：甲/乙/基石

## Sample Output
```
【某AI初创 港股IPO 询价建议】
发行规模: 1.2亿股 | 指导价 HK$32-38
估值区间 (by PS 10-12x):
  - PS 10x: HK$30
  - PS 12x: HK$36 ✅合理
可比公司: 商汤/第四范式/创新奇智
基石投资者: 2家, 认购40%
市场情绪: 超额认购预期 25-40x
首日建议:
  - 机构报价: HK$36 (上限80%)
  - 预计打新收益: +8%~15%
  - 破发概率: 15% (AI板块近期热度高)
```
