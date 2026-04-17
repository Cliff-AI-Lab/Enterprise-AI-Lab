---
name: 学术抄袭侦测
name_en: Academic Plagiarism Detector
type: Composite Application
industry: Education
composed_of: [学术论文助手, AI模型评测师, 知识问答专家]
source_refs: [Narratologist, Model QA Specialist]
apis: [CrossRef, Semantic Scholar, HuggingFace]
emoji: 🔎
---

# 🔎 学术抄袭侦测 Academic Plagiarism Detector

## Use Case
高校/期刊/培训: 论文相似度+AI生成内容识别+引用规范审查。

## Agent Composition
```
[学术论文助手] ← Narratologist (academic)
[AI模型评测师] ← Model QA Specialist
[知识问答专家] ← Psychologist
```

## Bound APIs
| API | Purpose |
|-----|------|
| CrossRef | 已发表文献 |
| Semantic Scholar | 学术图谱 |
| HuggingFace | AI生成检测模型 |

## 核心工作流
1. **文档上传**：PDF/DOC解析
2. **库匹配**：文献/网络/AIGC
3. **相似度**：全文/段落/句子
4. **引用规范**：APA/IEEE/MLA
5. **报告**：可疑段落标注

## Sample Output
```
【硕士论文查重报告】
作者: 张某某 | 学校: XX大学
字数: 38,200字
总相似率: 14.2% (学校阈值20% ✅)
分维度:
  - 与已发表文献相似: 8.7%
  - 与网络内容相似: 3.5%
  - AI生成内容识别: 12% (偏高⚠️)
    - 引言部分 AI生成概率85%
    - 文献综述 AI 概率68%
  - 自引: 2.0%
标注:
  - 红色段落: 0处 (>50%相似)
  - 橙色段落: 8处 (20-50%)
  - 黄色段落: 32处 (<20%)
引用规范:
  - 88条文献, APA格式
  - 4处引用不规范 → 标注修改
结论: 通过但建议修改AI生成明显段落
```
