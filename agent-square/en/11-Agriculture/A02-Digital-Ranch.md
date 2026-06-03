---
name: 数字牧场
name_en: Digital Ranch
type: Composite Application
industry: Agriculture
composed_of: [畜牧健康管理师, 数据采集工程师, 工艺优化师, 碳排放分析师]
source_refs: [Healthcare Customer Service, Data Engineer, Workflow Optimizer]
apis: [ThingSpeak, OpenFDA, Carbon Interface]
emoji: 🐄
---

# 🐄 数字牧场 Digital Ranch

## Use Case
规模化奶牛/肉牛/生猪场: 个体追踪+精准饲喂+疾病预警+环保合规。

## Agent Composition
```
[畜牧健康管理师] ← Healthcare Customer Service
[数据采集工程师] ← Data Engineer
[工艺优化师] ← Workflow Optimizer
[碳排放分析师] ← Financial Analyst
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 体征IoT |
| OpenFDA | 兽药 |
| Carbon Interface | 甲烷排放 |

## 核心工作流
1. **个体档案**：RFID耳标
2. **精准饲喂**：TMR按需
3. **繁殖管理**：发情/配种/妊娠
4. **粪污处理**：沼气/有机肥
5. **碳足迹**：每公斤牛奶CO2e

## Sample Output
```
【万头奶牛场 年度运营】
在栏: 10,800头 (泌乳 5,400)
产奶: 35,000 吨/年
单产: 11.5吨/头·年 (全国领先)
经济:
  - 营收 ¥1.8亿
  - 毛利率 38%
  - 每头终生利润 ¥28K
健康管理:
  - 死亡率 <1.5% (行业3%)
  - 年繁殖率 85% ✅
碳排放:
  - 全场 52,000 tCO2e/年
  - 每kg奶碳强度 1.5 kgCO2e (低于行业)
  - 沼气发电 + 粪肥还田
环保:
  - 废水处理达标排放
  - 异味控制投诉 0
```
