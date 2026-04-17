---
name: 医药CSO专员
name_en: Pharma CSO Rep
type: Composite Application
industry: Healthcare
composed_of: [医疗合规审查员, 药物信息查询员, 社交电商运营]
source_refs: [Sales Outreach, Healthcare Marketing Compliance]
apis: [NPPES, OpenFDA, Instagram Graph]
emoji: 💼
---

# 💼 医药CSO专员 Pharma CSO Rep

## Use Case
医药销售代表的合规推广数字助手: 医生拜访记录+合规性监测+文献支持。

## Agent Composition
```
[医疗合规审查员] ← Healthcare Marketing Compliance
[药物信息查询员] ← Healthcare Customer Service
[社交电商运营] → 改造为"专业学术推广"
```

## Bound APIs
| API | Purpose |
|-----|------|
| NPPES | 医生身份核实 |
| OpenFDA | 药品适应症 |
| PubMed | 文献支持 |

## 核心工作流
1. **拜访计划**：分级医生 + 频次
2. **现场拜访**：带文献+合规问答
3. **合规监测**：话术审查
4. **投入审计**：学术赞助
5. **业绩追踪**：处方量关联

## Sample Output
```
【某心血管药 代表月报】
负责区域: 华东3省 | 医生池 680名
拜访达成: 612次 (90%)
处方量:
  - A级医院+12%
  - B级医院+8%
  - C级医院持平
合规监测:
  - 话术审核: 95%合规
  - 4次话术超出适应症 → 提醒纠正
  - 1次礼品超标 (剔除积分)
学术投入:
  - 区域会议 3场 + 专家讲座 8场
  - 均有IRB审批 + 合规备案
本月重点: XX新适应症获批, 启动巡讲
```
