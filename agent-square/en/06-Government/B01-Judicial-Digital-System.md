---
name: 司法数字化
name_en: Judicial Digital System
type: Composite Application
industry: Government
composed_of: [法律文书审查员, 政务翻译官, 文档生成专家, 知识问答专家]
source_refs: [Legal Document Review, Legal Client Intake, Legal Billing & Time Tracking(specialized)]
apis: [CourtListener, Harvard CAP, LibreTranslate, PDFMonkey]
emoji: ⚖️
---

# ⚖️ 司法数字化 Judicial Digital System

## Use Case
法院/检察院/律所: 案件管理+类案检索+裁判预测+文书生成。

## Agent Composition
```
[Legal Document Review] ← specialized
[Legal Client Intake] ← specialized
[Legal Billing & Time Tracking] ← specialized
[政务翻译官] ← Language Translator
```

## Bound APIs
| API | Purpose |
|-----|------|
| CourtListener | 美国判例 |
| Harvard CAP | 历史案例 |
| PDFMonkey | 文书生成 |

## 核心工作流
1. **案件立案**：电子材料
2. **类案检索**：AI相似度
3. **争议焦点**：自动识别
4. **裁判预测**：辅助判断
5. **文书生成**：判决书模板

## Sample Output
```
【某中级法院 信息化月报】
收案: 2,400件 | 结案 2,280件
电子卷宗率: 98%
类案推送:
  - 法官使用率 82%
  - 裁判引用相似案件 68%
审判效率:
  - 平均审理周期: 92天 (↓18天)
  - 执行到位率 68%
文书质量:
  - AI辅助草拟 70%
  - 法官修改率 35%
  - 裁判文书上网率 95%
类案同判率:
  - 同类刑事 91%
  - 同类民事 78%
公开:
  - 庭审直播 820场
  - 裁判文书网上传 合规
```
