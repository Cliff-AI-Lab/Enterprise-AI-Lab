---
name: 跨境汇款合规助手
name_en: Cross-border Remittance Compliance
type: Composite Application
industry: Finance
composed_of: [外汇交易助手, 风控合规官, 税务筹划师]
apis: [ExchangeRate-API, OpenSanctions, RestCountries]
emoji: 🌐
---

# 🌐 跨境汇款合规助手 Cross-border Remittance Compliance

## Use Case
留学家庭/跨境电商/自由职业者的境外收付款合规检查+最优路径。

## Agent Composition
```
[外汇交易助手] → 汇率锁定
[风控合规官] → 收款方筛查
[税务筹划师] → CRS/申报
```

## Bound APIs
| API | Purpose |
|-----|------|
| ExchangeRate-API | 实时汇率 |
| OpenSanctions | 对方制裁筛查 |
| RestCountries | 目的地合规 |

## 核心工作流
1. **资金用途**：留学/贸易/投资
2. **收款方筛查**：制裁/PEP
3. **路径选择**：银行/Wise/PayPal
4. **费率+汇率**：综合成本
5. **税务提醒**：CRS/20万阈值

## Sample Output
```
【跨境汇款方案 - 王女士给子女】
金额: ¥100,000 → 美国
目的: 留学生活费 (合规)
用途申报: 因私购汇5万美元额度内 ✅
对方核验:
  - 收款人: 王某某 (在读证明)
  - 收款行: Chase USA (非制裁)
路径对比:
  A. 银行汇款: 费用 ¥420, 汇率7.24, 3-5天
  B. Wise: 费用 ¥180, 汇率7.22, 1天 ✅推荐
  C. PayPal: 费用 ¥580, 汇率7.15, 即时
合规:
  - 5万美元内免购汇外管申报
  - 美国持卡:利息<$10不报税
建议: 选B, 省 ¥240 + 快2天
```
