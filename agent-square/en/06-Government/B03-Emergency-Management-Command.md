---
name: 应急管理指挥
name_en: Emergency Management Command
type: Composite Application
industry: Government
apis: [NASA EONET, OpenWeatherMap, Disease.sh]
emoji: 🚨
---

# 🚨 应急管理指挥 Emergency Management Command

## Use Case
政府应急管理部门的地震/洪水/台风/火灾等综合应急指挥。

## Core Capabilities
- 灾情实时感知
- 物资调配
- 救援力量联动
- 灾后重建

## Bound APIs
| API | Purpose |
|-----|------|
| NASA EONET | 自然灾害 |
| OpenWeatherMap | 气象 |
| Disease.sh | 疫情应急 |

## Sample Output
```
【某省应急指挥 季报】
处置事件: 42起
  - 气象灾害 18
  - 森林火灾 8
  - 地质灾害 6
  - 公共卫生 4
  - 事故灾难 6
响应:
  - 启动I/II级 4次
  - 启动III/IV级 18次
物资:
  - 应急仓储 120个 | 物资充足率 94%
  - 调配到灾区 48次
力量协同:
  - 消防救援 4万人次
  - 武警+解放军 支援3次
预警准确率: 88%
```
