---
name: 中医AI问诊
name_en: TCM AI Consultation
type: Composite Application
industry: Healthcare
composed_of: [患者服务助手, 药物信息查询员, 知识问答专家]
source_refs: [Healthcare Customer Service, Psychologist(academic)]
apis: [Disease.sh, Wikipedia, Wolfram Alpha]
emoji: 🍵
---

# 🍵 中医AI问诊 TCM AI Consultation

## Use Case
结合传统中医辨证论治+现代数据的智能问诊系统，给出体质辨识+膳食调理+穴位建议。

## Agent Composition
```
[患者服务助手] ← Hospitality Guest Services
[药物信息查询员] ← Healthcare Customer Service
[知识问答专家] ← Psychologist / Historian
```

## Bound APIs
| API | Purpose |
|-----|------|
| Wikipedia | 中药/穴位百科 |
| Disease.sh | 症状参考 |
| 中医典籍 (本地) | 辨证逻辑 |
| Edamam (Food) | 食疗 |

## 核心工作流
1. **四诊问卷**：望闻问切数字化
2. **体质辨识**：九种体质+症候
3. **辨证论治**：六经/脏腑
4. **方剂推荐**：OTC+食疗
5. **免责提示**：严重病转诊

## Sample Output
```
【AI中医辨证 - 王女士 38岁】
主诉: 失眠多梦, 月经量少, 畏冷
舌象: 淡白胖嫩 (模型分析上传照片)
脉诊(问卷): 细弱
体质辨识: 阳虚+气血两虚 (概率83%)
证型: 心脾两虚 + 肾阳不足
调理方案:
  中成药 (OTC):
    - 归脾丸 (健脾养心)
    - 桂附地黄丸 (温肾)
  食疗:
    - 当归生姜羊肉汤 周1-2次
    - 桂圆红枣粥 每日早餐
  穴位按摩:
    - 三阴交, 神门, 足三里, 关元 每日10分钟
  生活:
    - 23点前入睡, 忌生冷
免责提示:
  - 持续2周无改善请线下就诊
  - 孕期/重病停用中药前咨询医师
```
