---
name: 预测性维护管家
name_en: Predictive Maintenance Steward
type: Composite Application
industry: Manufacturing
composed_of: [设备运维工程师, 数据采集工程师, AI模型评测师]
apis: [ThingSpeak, HuggingFace, UptimeRobot]
emoji: 🔮
---

# 🔮 预测性维护管家 Predictive Maintenance Steward

## Use Case
基于振动/温度/电流等多传感器，提前预测轴承、电机、泵的故障，减少非计划停机。

## Agent Composition
```
[数据采集工程师] → 振动/温度/电流采集
[AI模型评测师] → 故障预测模型
[设备运维工程师] → 工单派发
```

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 传感数据 |
| HuggingFace | 时序异常模型 |
| UptimeRobot | 状态看板 |

## 核心工作流
1. **关键设备选定**：ABC分类
2. **传感器加装**：振/温/流
3. **基线学习**：30天稳态
4. **偏离检测**：马氏距离/自编码
5. **剩余寿命(RUL)**：天/小时

## Sample Output
```
【关键设备健康排行】
监测设备: 286台 | 在线: 284
故障风险TOP:
  🔴 设备#C-102 压缩机
     RUL 预计 11天, 概率82%
     推荐动作: 本周末计划停机更换轴承
     备件库存: 2套 ✅
  🟠 设备#M-045 电机
     RUL 预计 45天
     推荐: 下月检修窗口
  🟠 设备#P-018 水泵
     振动频谱出现 1.2x谐波
     建议复检
预防性维护效益(本月):
  - 避免非计划停机 3次
  - 减少停机损失 ¥380万
  - MTBF提升18%
```
