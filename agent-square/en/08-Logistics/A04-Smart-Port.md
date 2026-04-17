---
name: 智慧港口
name_en: Smart Port
type: Composite Application
industry: Logistics
composed_of: [运力调度员, 数据采集工程师, 路径规划师, 设备运维工程师]
source_refs: [Project Shepherd, Data Engineer, SRE]
apis: [ThingSpeak, OpenRouteService, OpenWeatherMap]
emoji: 🏗️
---

# 🏗️ 智慧港口 Smart Port

## Use Case
自动化集装箱港口: 船舶调度、岸桥自动化、AGV转运、堆场优化。

## Agent Composition
```
[运力调度员] ← Project Shepherd
[设备运维工程师] ← SRE
[数据采集工程师] ← Data Engineer
[路径规划师] ← Geographer
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 设备数据 |
| OpenRouteService | AGV路径 |
| OpenWeatherMap | 风力预警 |

## 核心工作流
1. **船舶预报**：抵港/离港计划
2. **泊位分配**：船长+吃水+优先级
3. **装卸计划**：岸桥/AGV协同
4. **堆场管理**：箱位优化
5. **设备监控**：预测性维护

## Sample Output
```
【智慧港口 日运营 2026-04-17】
靠泊船舶: 18 艘 | 在港 12 | 等泊 6
集装箱吞吐: 48,200 TEU
效率KPI:
  - 船时效率: 182 TEU/小时 (↑12%)
  - 装卸平均时间: 24小时/船
  - AGV利用率: 82%
自动化程度:
  - 岸桥自动化率 76%
  - 堆场无人化率 92%
  - 闸口自动识别 98%
设备维护:
  - 3台岸桥预防性维护
  - 1台AGV故障 (48分钟内恢复)
预警:
  - 4/18 预计8级风 → 停吊1小时窗口
  - 某船申报提前到港, 泊位重排
```
