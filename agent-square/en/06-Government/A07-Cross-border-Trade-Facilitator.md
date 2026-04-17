---
name: 跨境贸易促进
name_en: Cross-border Trade Facilitator
type: Composite Application
industry: Government
composed_of: [关务报关员, 政策研究员, 公共数据分析师, 外汇交易助手]
source_refs: [Legal Compliance Checker, Government Digital Presales]
apis: [UK Trade Tariff, ExchangeRate-API, RestCountries]
emoji: 🌍
---

# 🌍 跨境贸易促进 Cross-border Trade Facilitator

## Use Case
商务部门/自贸区/外贸企业的RCEP/CPTPP政策解读+通关便利化+出口退税辅导。

## Agent Composition
```
[关务报关员] ← Legal Compliance Checker
[政策研究员] ← Government Digital Presales
[公共数据分析师] ← Analytics Reporter
[外汇交易助手] ← FP&A Analyst
```

## Bound APIs
| API | Purpose |
|-----|------|
| UK Trade Tariff | 各国税率 |
| ExchangeRate-API | 汇率 |
| RestCountries | 贸易伙伴信息 |

## 核心工作流
1. **贸易协定**：自贸新规+税差
2. **HS优选**：合规前提下最低税率
3. **原产地证**：RCEP/FTA证书
4. **单证便利**：电子化+无纸化
5. **退税辅导**：流程指引

## Sample Output
```
【某市进出口月度简报】
进出口额: $58亿 (↑12% YoY)
  - 出口 $36亿 (机电/电子/服装)
  - 进口 $22亿 (半导体/原料/设备)
主要贸易伙伴: 东盟/美/欧/日
RCEP红利:
  - 使用RCEP证出口 ¥24亿 (¥0.8亿关税节省)
  - 韩日进口 减免¥0.5亿
通关便利:
  - 通关时长 进口4.2h / 出口 1.8h (↓30%)
  - 提前申报率 88%
退税:
  - 应退 ¥12.4亿 (已办结 95%)
  - 平均退税周期 9天 (↓3天)
企业辅导: 开展RCEP培训12场 (480家企业)
```
