---
name: 产品增长分析
name_en: Product Growth Analytics
type: Composite Application
industry: Technology
composed_of: [数据可视化师, AI模型评测师, 消费者洞察专家]
source_refs: [Product Manager(product), Analytics Reporter, Trend Researcher, Feedback Synthesizer]
apis: [NewsAPI, Reddit API, HuggingFace]
emoji: 📈
---

# 📈 产品增长分析 Product Growth Analytics

## Use Case
SaaS/消费级App的增长团队: 漏斗+留存+PMF+北极星+A/B实验平台。

## Agent Composition
```
[数据可视化师] ← Analytics Reporter
[AI模型评测师] ← Model QA Specialist
[消费者洞察专家] ← Trend Researcher
[Feedback Synthesizer] ← product
```

## Bound APIs
| API | Purpose |
|-----|------|
| Reddit API | 用户声音 |
| NewsAPI | 市场趋势 |
| HuggingFace | NLP情感/话题 |

## 核心工作流
1. **北极星指标**：定义+追踪
2. **漏斗分析**：获客/激活/留存/营收/推荐
3. **群组(cohort)留存**：1/7/30日
4. **A/B实验**：多臂老虎机
5. **用户反馈挖掘**：评论/工单聚类

## Sample Output
```
【某SaaS增长月报】
北极星: WAU 周活 82,000 (↑8% MoM)
AARRR漏斗:
  - 获客 CAC $32
  - 激活 38% (新注册→试用)
  - 留存 W12 46%
  - 营收 ARPU $48/月
  - 推荐 NPS 54
A/B实验本月 8个:
  - Onboarding简化: CVR +18% ✅ 已发布
  - 定价页A/B: 年付方案 +32%
  - Paywall时机: 用户第3次使用最优
用户反馈洞察:
  - Top痛点: 导出功能慢 (提及率12%)
  - Top爱点: AI建议质量 (NPS推手)
  - 竞品讨论: 竞品X新功能 被280用户提及
下月重点: 企业版定价 + 导出性能
```
