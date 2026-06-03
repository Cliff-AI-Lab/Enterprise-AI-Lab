---
name: 一对一AI家教
name_en: Personalized AI Tutor
type: 组合应用
industry: 教育
composed_of: [知识问答专家, 课程设计师, 多语言翻译官, AI模型评测师]
source_refs: [Psychologist(academic), Corporate Training Designer]
apis: [Wolfram Alpha, Wikipedia, Dictionary APIs, HuggingFace]
emoji: 👩‍🏫
---

# 👩‍🏫 一对一AI家教 Personalized AI Tutor

## 应用场景
K12/语培的个性化AI家教: 学情诊断+自适应训练+苏格拉底式引导。

## Agent组合
```
[知识问答专家] ← Psychologist
[课程设计师] ← Corporate Training Designer
[多语言翻译官] ← Language Translator
[AI模型评测师] ← Model QA Specialist
```

## 绑定API
| API | 用途 |
|-----|------|
| Wolfram Alpha | 数学/物理计算 |
| Wikipedia | 百科 |
| Dictionary API | 词义/例句 |
| HuggingFace | 语音评测 |

## 核心工作流
1. **入学诊断**：知识图谱评测
2. **学习画像**：强弱项/习惯
3. **自适应推题**：难度阶梯
4. **苏格拉底引导**：启发式
5. **家长报告**：周度进展

## 典型输出
```
【学生 小明 五年级 数学周报】
学习时长: 4.8小时 | 完成 126题
进步:
  ✅ 分数运算 从65% → 88%
  ✅ 应用题阅读理解 +2个等级
待加强:
  ⚠️ 几何体积 准确率55% (薄弱)
  ⚠️ 速度问题 典型错误: 单位换算
本周 AI互动片段:
  学生: "不知道这道题为什么错"
  AI:  "别急，我们先读题一次好吗? 题目中..."
        (通过4步反问引导正确解法)
推荐下周:
  - 几何体积专项 30分钟×5天
  - 单位换算小游戏 每日10分钟
  - 预习: 小数除法
家长建议: 继续保持每日练习, 避免刷题
```
