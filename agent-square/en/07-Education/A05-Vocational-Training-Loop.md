---
name: 职业培训闭环
name_en: Vocational Training Loop
type: Composite Application
industry: Education
composed_of: [课程设计师, AI模型评测师, 销售数据分析师]
source_refs: [Corporate Training Designer, Recruitment Specialist]
apis: [Hipolabs Universities, HuggingFace, JSONBin]
emoji: 🧑‍💻
---

# 🧑‍💻 职业培训闭环 Vocational Training Loop

## Use Case
编程/设计/AI等新兴技能的全链路培训: 招生→教学→项目→就业推荐。

## Agent Composition
```
[课程设计师] ← Corporate Training Designer
[AI模型评测师] ← Model QA Specialist
[销售数据分析师] ← Recruitment Specialist
```

## Bound APIs
| API | Purpose |
|-----|------|
| GitHub API | 学员作品 |
| HuggingFace | 能力评估 |
| Remotive Jobs | 岗位对接 |

## 核心工作流
1. **招生筛选**：Free试听
2. **分班教学**：直播+录播
3. **项目实战**：开源作品
4. **能力认证**：考评体系
5. **就业推荐**：合作企业

## Sample Output
```
【AI工程师训练营 22期 结业报告】
招生: 120人 | 结业 94人 (完训率78%)
课程 16周:
  - Python/Data 4周
  - ML/DL/LLM 8周
  - 项目实战 3周
  - 面试辅导 1周
项目成果:
  - 94人完成毕业项目 (GitHub开源)
  - 优秀项目 18个 (受企业关注)
就业数据 (结业后3个月):
  - 就业率 82% (77人)
  - 平均薪酬 ¥22K/月 (北京/上海)
  - 最高 ¥45K (某AI独角兽)
校企合作:
  - 合作企业 86家
  - 专场招聘 12场
  - 定向输送 32人
口碑:
  - NPS 72
  - 推荐率 58%
```
