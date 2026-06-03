---
name: 光储一体化规划
name_en: Solar-Storage Integrated Planner
type: Composite Application
industry: Energy
composed_of: [太阳能评估师, 电力负荷预测员, 新能源投研员]
apis: [NREL PVWatts, EIA, OpenWeatherMap]
emoji: 🔋
---

# 🔋 光储一体化规划 Solar-Storage Integrated Planner

## Use Case
工商业/户用屋顶光伏+储能系统设计工具，峰谷套利+备电+绿电认证。

## Agent Composition
```
[太阳能评估师] → 装机+发电模拟
[电力负荷预测员] → 负荷曲线分析
[新能源投研员] → 电芯选型+成本
```

## Bound APIs
| API | Purpose |
|-----|------|
| NREL PVWatts | 发电模拟 |
| OpenWeatherMap | 辐照 |
| EIA | 电价 |

## 核心工作流
1. **负荷分析**：15分钟级日曲线
2. **光伏匹配**：自用率优化
3. **储能设计**：容量/倍率
4. **经济性**：峰谷套利+降费
5. **应急**：备电时长

## Sample Output
```
【商业综合体光储方案】
建筑: 8万㎡, 年电量800万kWh
光伏 800kWp 屋顶 5,600㎡:
  - 年发95万kWh | 自用率92%
  - 度电成本 ¥0.25
储能 1MWh / 500kW:
  - 峰谷套利 (¥0.88 vs ¥0.32)
  - 日循环1.2次
  - 年度收益 ¥35万
综合效益:
  - 年减电费 ¥68万 (光+储)
  - 总投资 ¥420万
  - 回收期 6.2年 | IRR 13.8%
  - 年减碳 540 tCO2e
应急: 断电可保核心负荷 4小时
```
