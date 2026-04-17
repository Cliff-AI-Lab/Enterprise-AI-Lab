---
name: 再保险精算
name_en: Reinsurance Actuary
type: Composite Application
industry: Finance
apis: [NASA EONET, OpenWeatherMap, Disease.sh]
emoji: ♻️
---

# ♻️ 再保险精算 Reinsurance Actuary

## Use Case
再保险公司的巨灾建模+定价+资本充足率管理。

## Core Capabilities
- 巨灾模型 (地震/台风/洪水)
- 条约/临分再保定价
- 巨灾债券设计
- 偿二代资本占用

## Bound APIs
| API | Purpose |
|-----|------|
| NASA EONET | 灾害事件 |
| OpenWeatherMap | 气象风险 |
| Disease.sh | 疫情风险 |

## Sample Output
```
【某再保公司 季度报告】
承保业务: 总保费 $2.8B
巨灾敞口:
  - 地震(CAT) $180亿 OEP 200年
  - 台风 $120亿
  - 洪水 $80亿
再保定价:
  - 比例合约 28%固定付
  - 超赔ROL 12-28%
巨灾债券发行:
  - 新增 $600M (3年)
  - 票息 6.8%
偿付能力: 208% (监管>100%)
```
