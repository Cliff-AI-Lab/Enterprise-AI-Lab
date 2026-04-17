---
name: 生猪全产业链
name_en: Swine Industry Value Chain
type: Composite Application
industry: Agriculture
composed_of: [畜牧健康管理师, 农产品行情分析师, 供应链策略师, 质量追溯专家]
source_refs: [Supply Chain Strategist, Financial Analyst]
apis: [ThingSpeak, Alpha Vantage, AfterShip]
emoji: 🐷
---

# 🐷 生猪全产业链 Swine Industry Value Chain

## Use Case
从母猪繁育→育肥→屠宰→分割→冷链→销售 全产业链数字化。

## Agent Composition
```
[畜牧健康管理师] → 生产管理
[农产品行情分析师] → 出栏时机
[供应链策略师] → 饲料+屠宰协同
[质量追溯专家] → 食品安全
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 环控/体征 |
| Alpha Vantage | 猪价/玉米 |
| AfterShip | 冷链 |

## 核心工作流
1. **繁育**：PSY管理
2. **育肥**：料肉比优化
3. **出栏调度**：价格最优
4. **屠宰分割**：胴体品质
5. **冷链销售**：渠道匹配

## Sample Output
```
【某生猪养殖集团 月度战报】
在栏: 120万头 (能繁母猪 8.2万)
PSY: 24.5 (行业均18)
出栏:
  - 本月 12万头
  - 均重 115kg
  - 当月均价 ¥14.8/kg
  - 月收入 ¥20.4亿
成本结构:
  - 饲料 65% (玉米+豆粕)
  - 人工 8%
  - 折旧+管理 15%
  - 其他 12%
完全成本 ¥13.2/kg | 毛利 ¥1.6/kg
MV:
  - 价格研判: 夏季淡季注意出栏节奏
  - 饲料锁价: 期货套保40%
屠宰+销售:
  - 自营白条肉 ¥6亿
  - 分割精深加工 ¥2亿
  - 品牌零售占比 18% (溢价+22%)
```
