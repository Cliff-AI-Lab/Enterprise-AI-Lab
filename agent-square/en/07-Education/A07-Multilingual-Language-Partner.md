---
name: 多语种陪练
name_en: Multilingual Language Partner
type: Composite Application
industry: Education
composed_of: [多语言翻译官, 知识问答专家, 一对一AI家教]
source_refs: [Language Translator, Psychologist]
apis: [LibreTranslate, Dictionary APIs, HuggingFace]
emoji: 🗣️
---

# 🗣️ 多语种陪练 Multilingual Language Partner

## Use Case
英/日/西/法/德/阿 等外语口语陪练: 语音评测、场景对话、语法纠错。

## Agent Composition
```
[多语言翻译官] ← Language Translator
[知识问答专家] ← Psychologist
[一对一AI家教] ← Corporate Training Designer
```

## Bound APIs
| API | Purpose |
|-----|------|
| LibreTranslate / DeepL | 翻译对照 |
| Dictionary API | 词典/例句 |
| HuggingFace | 语音识别+评分 |

## 核心工作流
1. **水平测评**：CEFR A1-C2
2. **场景选择**：出国/商务/考试
3. **对话练习**：30分钟/次
4. **评分反馈**：发音/语法/词汇
5. **错题本**：个性化复习

## Sample Output
```
【日语口语陪练 今日课程总结】
场景: 居酒屋点菜 (N3-N2水平)
对话时长: 32分钟 | 发言28次
流利度: 3.8/5 (vs 上次 3.5)
准确度:
  - 发音: 82分 (ら行需改善)
  - 语法: "敬语连用形"出错3次 → 专题复习
  - 词汇: 新学 12个 (刺身/厨师/结账)
亮点:
  - "すみません、おすすめは何ですか" 自然使用 ✅
  - 主动询问食材过敏 ✅
待改进:
  - 避免中式思维直译
  - "~と思います" 过度使用
明日计划:
  - 听力: 居酒屋实景音频 (5分钟)
  - 词汇: 和食菜单词汇50个
  - 口语: 复习敬语 → 新场景"和同事的对话"
```
