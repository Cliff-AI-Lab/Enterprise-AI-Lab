---
name: 无人农机调度
name_en: Autonomous Farm Machinery Fleet
type: Composite Application
industry: Agriculture
composed_of: [农机调度师, 路径规划师, 数据采集工程师, 设备运维工程师]
source_refs: [Fleet Dispatcher, Data Engineer, SRE]
apis: [OpenRouteService, ThingSpeak, OpenWeatherMap]
emoji: 🤖
---

# 🤖 无人农机调度 Autonomous Farm Machinery Fleet

## Use Case
基于RTK+AI的无人农机协同作业: 播种/植保/收割全流程少人/无人化。

## Agent Composition
```
[农机调度师] ← Project Shepherd
[路径规划师] ← Geographer
[数据采集工程师] ← Data Engineer
[设备运维工程师] ← SRE
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenRouteService | 地块作业路径 |
| ThingSpeak | 农机状态流 |
| OpenWeatherMap | 气象窗口 |

## 核心工作流
1. **地块管理**：电子围栏
2. **路径规划**：最少重叠+转头
3. **集群作业**：多机协同
4. **状态监控**：故障预警
5. **无人交接**：换班/加油/加料

## Sample Output
```
【万亩智慧农场 无人作业日报】
在用农机: 18台 (全部L4自动驾驶)
  - 无人拖拉机 8台
  - 无人植保机 6台 (无人机)
  - 无人收割机 4台
今日作业:
  - 拖拉机播种: 1,800亩 | 单机UPH 45亩/小时
  - 植保喷洒: 2,400亩 | 单机UPH 120亩/小时
  - 收割: 1,200亩
人工占用:
  - 传统: 80人日 | 现: 4人日 (监控+装卸)
异常:
  - 1台无人机电池低预警 → 自动返航
  - 1台拖拉机RTK信号弱 → 人工介入10分钟
效率:
  - 相比传统 节省40%时间 + 降低60%成本
  - 作业精度 ±2.5cm (RTK)
```
