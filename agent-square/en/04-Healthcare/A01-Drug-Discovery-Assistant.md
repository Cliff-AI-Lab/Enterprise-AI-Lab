---
name: 新药研发辅助系统
name_en: Drug Discovery Assistant
type: Composite Application
industry: Healthcare
composed_of: [医学文献研究员, 临床试验分析师, AI模型评测师, 数据采集工程师]
source_refs: [Narratologist(academic), Data Engineer(engineering), Model QA Specialist(specialized)]
apis: [PubMed, ClinicalTrials.gov, OpenFDA, HuggingFace]
emoji: 🧬
---

# 🧬 新药研发辅助系统 Drug Discovery Assistant

## Use Case
药企研发部门的靶点挖掘→分子筛选→临床前→IND→临床I/II/III 全流程AI助手。

## Agent Composition (来自 agency-agents)
```
[医学文献研究员] ← Narratologist / Historian (academic)
[临床试验分析师] ← Data Engineer (engineering)
[AI模型评测师] ← Model QA Specialist (specialized)
[数据采集工程师] ← Data Engineer (engineering)
```

## Bound APIs (来自 public-apis)
| API | 类别 | 用途 |
|-----|------|------|
| PubMed E-Utils | Science & Math | 文献/摘要 |
| ClinicalTrials.gov | Health | 临床试验库 |
| OpenFDA | Health | 药品审评 |
| HuggingFace | Machine Learning | 分子模型推理 |
| CrossRef | Science & Math | 引文图谱 |

## 核心工作流
1. **靶点挖掘**：文献+组学关联分析
2. **分子设计**：AI生成+虚拟筛选
3. **成药性评估**：ADMET 预测
4. **临床对标**：同靶点在研清单
5. **IND申报辅助**：文献证据包

## Sample Output
```
【GLP-1/GIP 双靶点 管线调研】
靶点证据:
  - PubMed: 562篇 (近3年)
  - 关键通路: cAMP/PKA双激活
  - 代谢收益: HbA1c↓1.6%, 体重↓15%
候选分子虚筛:
  - 10,000个骨架 → 结合能<-9 kcal/mol 筛得 28个
  - ADMET OK: 12个
  - 重点跟踪3个
临床对标:
  - 已上市: Tirzepatide (礼来)
  - 在研III期: Retatrutide (礼来, 三靶点)
  - 在研II期: Mazdutide (礼来/信达)
差异化建议: 探索口服 或 延长半衰期 (月度给药)
```
