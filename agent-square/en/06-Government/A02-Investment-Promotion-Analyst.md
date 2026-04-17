---
name: 招商引资分析师
name_en: Investment Promotion Analyst
type: Composite Application
industry: Government
composed_of: [政策研究员, 公共数据分析师, 新闻聚合编辑]
source_refs: [Government Digital Presales, Trend Researcher]
apis: [USASpending, OpenCorporates, NewsAPI]
emoji: 🏢
---

# 🏢 招商引资分析师 Investment Promotion Analyst

## Use Case
地方政府招商部门的产业链图谱+目标企业画像+精准邀约。

## Agent Composition
```
[政策研究员] ← Government Digital Presales
[公共数据分析师] ← Analytics Reporter
[新闻聚合编辑] ← Trend Researcher
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenCorporates | 全球公司信息 |
| USASpending | 企业政府合同 |
| NewsAPI | 扩产/新项目新闻 |
| SEC EDGAR | 上市企业计划 |

## 核心工作流
1. **产业链梳理**：目标产业上下游
2. **企业画像**：规模/扩张动向
3. **政策匹配**：本地优惠+需求
4. **精准邀约**：决策人+时点
5. **跟踪闭环**：签约-开工-达产

## Sample Output
```
【半导体封测产业 招商月报】
目标池: 142家 (全球) | 活跃意向 28家
本月里程碑:
  ✅ 某台资A 签约 投资 ¥18亿 (2000人)
  ✅ 韩资B 落地选址确定
  🟡 美资C 高管已到访2次
产业链图谱:
  - 现有: 封测厂3家 | 材料2家 | 设备1家
  - 缺口: EDA软件、先进封装载板
  - 目标: 引入5家填补
精准捕捉:
  - 某公司近期公告扩产计划 → 已主动对接
  - 某公司大陆事业群调整 → 抢抓窗口
政策工具箱:
  - 土地 / 厂房 / 税收 / 人才 / 投贷联动
今年KPI: 签约50亿 (已完成62%)
```
