---
name: 精准医疗顾问
name_en: Precision Medicine Advisor
type: Composite Application
industry: Healthcare
composed_of: [药物信息查询员, 医学文献研究员, 健康数据分析师]
source_refs: [Healthcare Customer Service, Narratologist]
apis: [OpenFDA, PubMed, ClinVar]
emoji: 🧑‍⚕️
---

# 🧑‍⚕️ 精准医疗顾问 Precision Medicine Advisor

## Use Case
为肿瘤/罕见病患者基于基因检测结果匹配精准靶向药+临床试验入组。

## Agent Composition
```
[药物信息查询员] ← Healthcare Customer Service
[医学文献研究员] ← Narratologist (academic)
[健康数据分析师] ← Analytics Reporter
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenFDA | 靶向药获批情况 |
| PubMed | 文献证据 |
| ClinicalTrials.gov | 临床试验入组 |

## 核心工作流
1. **基因报告解读**：变异清单
2. **驱动突变识别**：致癌/耐药
3. **药物匹配**：FDA/NMPA获批+压线试验
4. **证据分级**：OncoKB / AMP
5. **个案报告**：给主诊医生

## Sample Output
```
【患者 个案 - 非小细胞肺癌 Stage IV】
基因检测 (NGS 549基因):
  - EGFR Exon19 del ← 驱动突变
  - TP53 突变 (co-mut)
  - 无耐药突变
靶向药匹配 (证据 LevelA):
  1. Osimertinib (首选, 一线)
  2. Gefitinib (二线备选, 若B/M低)
  3. Erlotinib
临床试验入组:
  - NCT0xxxx EGFR一线联合 (上海, 招募中)
  - NCT0yyyy 靶向+免疫 (北京II期)
预后估计: PFS中位 19个月 (vs 化疗 5个月)
医保: Osimertinib 已进医保, 自费约 ¥1.5万/月
已推送至主诊医生: 张医生 (ID 1234)
```
