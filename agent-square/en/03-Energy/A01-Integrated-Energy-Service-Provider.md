---
name: 综合能源服务商
name_en: Integrated Energy Service Provider
type: Composite Application
industry: Energy
composed_of: [太阳能评估师, 能效审计师, 电力负荷预测员, 碳排放分析师]
apis: [NREL PVWatts, EIA, OpenWeatherMap, Carbon Interface]
emoji: 🏭
---

# 🏭 综合能源服务商 Integrated Energy Service Provider

## Use Case
工业园区/大客户的光伏+储能+充电+节能+碳资产一体化方案商。

## Agent Composition
```
[能效审计师] → 基准用能诊断
[太阳能评估师] → 光伏设计
[电力负荷预测员] → 储能容量设计
[碳排放分析师] → 碳中和路径
```

## Bound APIs
| API | Purpose |
|-----|------|
| NREL PVWatts | 光伏发电模拟 |
| EIA | 电价数据 |
| OpenWeatherMap | 气象 |
| Carbon Interface | 减碳量核算 |

## 核心工作流
1. **能源诊断**：过去3年用能基线
2. **方案设计**：光+储+充+节能组合
3. **投资测算**：自投/合作/EMC
4. **建设实施**：EPC交钥匙
5. **运营运维**：能源管理平台

## Sample Output
```
【某工业园综合能源方案】
园区基本: 年用电 3,800万kWh, 电费 ¥2,850万
设计:
  - 光伏 12MWp → 年发1,440万kWh (自用率85%)
  - 储能 8MWh → 削峰填谷套利
  - 快充 20把 → 电车员工+对外
  - LED/空调改造 → 省电10%
财务 (25年):
  - 总投资: ¥6,800万
  - 年节能收益: ¥1,680万
  - IRR: 15.8% | 回收期 4.8年
  - 碳减量: 9,200 tCO2e/年
模式: 合同能源管理 (EMC 7:3客分成)
```
