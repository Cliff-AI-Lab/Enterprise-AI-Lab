---
name: ESG投资筛选师
name_en: ESG Investment Screener
type: 组合应用
industry: 金融
composed_of: [股票分析师, 碳排放分析师, 风控合规官, 舆情监控员]
apis: [SEC EDGAR, Carbon Interface, NewsAPI]
emoji: 🌿
---

# 🌿 ESG投资筛选师 ESG Investment Screener

## 应用场景
ESG基金/责任投资产品的股票池筛选，环境/社会/治理三维打分。

## Agent组合
```
[股票分析师] → 基本面
[碳排放分析师] → 环境E维度
[风控合规官] → 治理G维度
[舆情监控员] → 社会S维度
```

## 绑定API
| API | 用途 |
|-----|------|
| SEC EDGAR | ESG披露 |
| Carbon Interface | 碳排放强度 |
| NewsAPI + GNews | 社会事件负面 |

## 核心工作流
1. **负面排除**：烟酒赌武器/化石
2. **ESG评分**：E(40)+S(30)+G(30)
3. **同业百分位**：分位数排名
4. **组合构建**：ESG+Alpha
5. **持续监控**：重大事件更新

## 典型输出
```
【ESG股票池 2026Q2 更新】
候选股票: 820 → 筛后 186只
Top10 (行业均衡):
  1. 宁德时代 E95 S82 G88
  2. 比亚迪 E90 S80 G85
  3. 台积电 E85 S86 G92
  ...
本季剔除:
  - 公司X: 爆出劳工纠纷, S降级
  - 公司Y: 审计意见保留, G降级
新纳入: 5家 (符合SBTi目标)
组合超额收益(ESG Alpha): +1.3% vs 沪深300
```
