---
name: 最后一公里
name_en: Last Mile Delivery
type: Composite Application
industry: Logistics
composed_of: [路径规划师, 运力调度员, 包裹追踪员, 客服智能助手]
source_refs: [Geographer, Customer Service]
apis: [OpenRouteService, AfterShip, LibreTranslate]
emoji: 📬
---

# 📬 最后一公里 Last Mile Delivery

## Use Case
快递驿站/智能柜/无人车的最后一公里交付，解决送货上门/暂存/代收。

## Agent Composition
```
[路径规划师] ← Geographer
[运力调度员] ← Project Shepherd
[包裹追踪员] ← Evidence Collector
[客服智能助手] ← Customer Service
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenRouteService | 小区内路径 |
| AfterShip | 包裹状态 |
| SMS APIs | 取件码通知 |

## 核心工作流
1. **到件分拣**：驿站/柜/上门
2. **智能柜存放**：格口分配
3. **用户选择**：柜/门/驿站
4. **入柜识别**：摄像头校验
5. **48小时清理**：超时提醒

## Sample Output
```
【某小区驿站 日运营】
入驿件数: 840件 | 柜存 320 | 上门 280 | 驿站取 240
柜存取件:
  - 平均存放 8.2小时
  - 超24小时: 32件 (提醒费)
  - 超48小时退回: 5件
客户偏好:
  - 23% 默认柜存
  - 38% 上门 (主要上班族夫妻家庭)
  - 39% 驿站
高峰: 19:00-21:00 取件 (占全天45%)
异常:
  - 12件投递错误 (重派)
  - 3件破损 (理赔启动)
满意度: 4.7/5
```
