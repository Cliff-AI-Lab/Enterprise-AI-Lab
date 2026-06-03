---
name: 可转债套利员
name_en: Convertible Bond Arbitrage
type: Composite Application
industry: Finance
composed_of: [股票分析师, 投资组合管理师]
apis: [Alpha Vantage, Twelve Data, Financial Modeling Prep]
emoji: 🔄
---

# 🔄 可转债套利员 Convertible Bond Arbitrage

## Use Case
可转债定价模型+Delta对冲+网格交易，风险低收益稳。

## Agent Composition
```
[股票分析师] → 正股波动率
[投资组合管理师] → 转债+正股对冲比
```

## Bound APIs
| API | Purpose |
|-----|------|
| Alpha Vantage | 正股价格/波动率 |
| Twelve Data | 转债报价 |
| FMP | 发行条款 |

## 核心工作流
1. **转股价值计算**：=正股 × 转股比
2. **债底计算**：纯债价值
3. **溢价分析**：转股溢价率/纯债溢价率
4. **Delta对冲**：买转债+卖正股
5. **条款博弈**：下修/回售

## Sample Output
```
【可转债机会扫描 2026-04-17】
筛选条件: 溢价率<10% + 余额>5亿 + YTM>0
TOP 5机会:
  1. 某科技转债
     价格 ¥112 | 转股溢价 -2.3% ✅负溢价
     策略: 买入转债 + 卖空正股 锁定套利
     预期收益: 1.2% (10天内)
  2. 某医药转债
     正股波动率↑, 理论价值低估
     建议: 买入 delta对冲0.7
强赎预警: 3只可能强赎, 注意止盈
```
