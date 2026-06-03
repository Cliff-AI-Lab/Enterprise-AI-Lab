---
name: 医疗器械研发
name_en: Medical Device R&D
type: Composite Application
industry: Healthcare
composed_of: [临床试验分析师, 医疗合规审查员, 数字孪生构建师]
source_refs: [Civil Engineer, Embedded Firmware Engineer, Data Engineer]
apis: [OpenFDA Device, ClinicalTrials, HuggingFace]
emoji: 🩺
---

# 🩺 医疗器械研发 Medical Device R&D

## Use Case
医疗器械公司从概念→样机→临床验证→注册上市全流程管理。

## Agent Composition
```
[Civil Engineer] ← specialized (结构设计)
[Embedded Firmware Engineer] ← engineering
[临床试验分析师] ← Data Engineer
[医疗合规审查员] ← Healthcare Marketing Compliance
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenFDA Device | 510k/PMA参考 |
| ClinicalTrials | 验证试验 |
| HuggingFace | AI算法开发 |

## 核心工作流
1. **需求定义**：临床+法规
2. **设计输入**：DHF
3. **样机+验证**：V&V
4. **临床试验**：IDE/CTD
5. **注册上市**：510k/PMA/CE/NMPA

## Sample Output
```
【某家用血压计 研发进展】
技术路线: 示波法 + AI房颤筛查
关键指标:
  - 准确度: ±3 mmHg (超BS EN 1060)
  - 房颤识别 灵敏度 96%, 特异度 98%
Timeline:
  ✅ M1-6: 设计+样机
  ✅ M7-9: V&V验证 通过
  🟡 M10-15: 临床试验 (N=1,200)
  🔲 M16-20: 注册申报
      FDA 510k / NMPA II类 / CE MDR
技术文件:
  - 设计历史文件(DHF) 完备
  - 风险管理 ISO 14971
  - 可用性工程 IEC 62366
  - 软件IEC 62304 Class B
成本预算:
  - BOM ¥42/台
  - 售价定位 ¥299 (大众市场)
  - 年产能 80万台
```
