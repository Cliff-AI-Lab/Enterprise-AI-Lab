---
name: 半导体晶圆厂
name_en: Semiconductor Fab
type: Composite Application
industry: Manufacturing
apis: [ThingSpeak, OpenCorporates, Alpha Vantage]
emoji: 💾
---

# 💾 半导体晶圆厂 Semiconductor Fab

## Use Case
半导体Foundry/IDM的良率+产能+客户分配+合规管理。

## Core Capabilities
- APC先进过程控制
- 缺陷诊断(DefectAI)
- 产能分配+承诺
- 出口管制合规

## Bound APIs
| API | Purpose |
|-----|------|
| ThingSpeak | 工艺SPC数据 |
| OpenCorporates | 客户合规 |
| Alpha Vantage | 行业景气 |

## Sample Output
```
【某Fab 月度】
晶圆产能: 10万片/月 (12寸)
主要工艺: 28nm/14nm/7nm
良率:
  - 28nm 98% | 14nm 95% | 7nm 88%
客户分配:
  - 美国客户 35%
  - 欧洲 22%
  - 中国大陆 28%
  - 其他 15%
出口合规:
  - EAR/BIS审核 100%通过
  - 高端客户实体清单排查
关键问题:
  - 人才短缺 (工程师缺口15%)
  - 地缘风险 (供应链+客户)
```
