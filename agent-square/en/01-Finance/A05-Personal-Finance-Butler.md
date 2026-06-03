---
name: 个人理财管家
name_en: Personal Finance Butler
type: Composite Application
industry: Finance
composed_of: [财务记账员, 税务筹划师, 投资组合管理师]
apis: [ExchangeRate-API, Alpha Vantage, Open Banking APIs]
emoji: 💳
---

# 💳 个人理财管家 Personal Finance Butler

## Use Case
新中产家庭财务管家：记账、预算、税务、投资、保险一站式。

## Agent Composition
```
[财务记账员] → 日常记账+分类
[税务筹划师] → 个税/年终奖优化
[投资组合管理师] → 闲钱配置
```

## Bound APIs
| API | Purpose |
|-----|------|
| Alpha Vantage | 基金/ETF跟踪 |
| ExchangeRate-API | 外币资产折算 |
| Open Banking APIs | 账户聚合 |

## 核心工作流
1. **账户聚合**：工资+信用卡+理财
2. **消费分类**：标签化+月度预算
3. **税务优化**：年终奖/专项附加
4. **投资建议**：现金/债/股配比
5. **保障检视**：保险缺口分析

## Sample Output
```
【陈女士 2026年3月家庭财务月报】
总资产: ¥186万 (↑0.8%) | 负债: ¥45万
收入: ¥48,000 | 支出: ¥22,800 | 储蓄率 52%
预算执行:
  - 餐饮 ¥3,200 (超支8%) ⚠️
  - 教育 ¥5,000 (达标)
  - 娱乐 ¥800 (节约)
理财建议:
  - 活期现金过多¥8万 → 买货币基金赚 ¥280/月
  - 子女教育金年金已达标 ✅
  - 重疾险保额缺口 ¥50万, 建议补充
税务提醒: 专项附加累计¥3,600未申报
```
