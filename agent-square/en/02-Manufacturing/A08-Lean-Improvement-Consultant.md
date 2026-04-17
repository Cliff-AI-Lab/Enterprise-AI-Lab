---
name: 精益改善顾问
name_en: Lean Improvement Consultant
type: Composite Application
industry: Manufacturing
composed_of: [工艺优化师, 质量检测员, 生产排程员]
apis: [QuickChart, HuggingFace, JSONBin]
emoji: 🎯
---

# 🎯 精益改善顾问 Lean Improvement Consultant

## Use Case
导入TPS精益文化，每周识别改善机会并跟踪PDCA。

## Agent Composition
```
[工艺优化师] → 价值流图VSM
[质量检测员] → 缺陷改善
[生产排程员] → 流水线平衡
```

## Bound APIs
| API | Purpose |
|-----|------|
| QuickChart | VSM/柱状/帕累托 |
| JSONBin | 改善提案数据库 |
| HuggingFace | 文本分类改善点 |

## 核心工作流
1. **现场诊断**：MUDA七大浪费
2. **立项**：改善提案评估
3. **实施**：5S/SMED/均衡化
4. **验证**：A/B对比
5. **固化**：SOP/培训

## Sample Output
```
【月度精益改善报告 2026-04】
提案收集: 186件 | 立项: 32件
已关闭: 24件 | 进行中: 8件
重点改善成果:
  1. 注塑车间 SMED: 换模 45→12分钟
     年化节省 820小时 ≈ ¥65万
  2. 装配线平衡: 瓶颈工位 120→95秒
     节拍提升 26%
  3. 包装线 5S改善: 找物时间↓60%
ROI均值: 8.2x (投入1块回8.2块)
下月主题: 均衡化生产 (Heijunka)
```
