---
name: 城配即时物流
name_en: Urban Instant Delivery
type: Composite Application
industry: Logistics
composed_of: [路径规划师, 运力调度员, 包裹追踪员, 客服智能助手]
source_refs: [Geographer, Project Shepherd, Customer Service]
apis: [OpenRouteService, OpenWeatherMap, AfterShip]
emoji: 🛵
---

# 🛵 城配即时物流 Urban Instant Delivery

## Use Case
美团闪购/京东达达/顺丰同城模式: 30分钟-2小时同城配送调度。

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
| OpenRouteService | 摩托车/自行车路径 |
| OpenWeatherMap | 恶劣天气限行 |
| AfterShip | 客户查单 |

## 核心工作流
1. **订单接入**：商家/平台
2. **骑手匹配**：距离+负荷
3. **路径推荐**：多单合并
4. **实时调度**：动态改派
5. **用户通知**：到达提醒

## Sample Output
```
【城配日报 2026-04-17】
订单量: 52万单 | 骑手活跃 4.2万
平均时效:
  - 30分钟达: 92%
  - 1小时达: 98%
  - 超时: 1.8%
单人日均: 12.4单 | ARPO骑手 ¥380/日
品类分布:
  - 外卖 45%
  - 商超 22%
  - 药品 15%
  - 数码 8%
  - 其他 10%
异常:
  - 暴雨时段 时效达标率↓至82%
  - 补贴骑手雨天单价 +¥2/单
客诉: 0.22% (主要送错/洒漏)
```
