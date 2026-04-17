---
name: 公共卫生应急
name_en: Public Health Emergency Response
type: Composite Application
industry: Government
composed_of: [疫情监控员, 健康数据分析师, 舆情监控员, 多语言翻译官]
source_refs: [Reality Checker, Analytics Reporter]
apis: [Disease.sh, WHO, NewsAPI, LibreTranslate]
emoji: 🚨
---

# 🚨 公共卫生应急 Public Health Emergency Response

## Use Case
疾控中心应急指挥: 传染病监测、病例追踪、公众告知、国际协同。

## Agent Composition
```
[疫情监控员] ← Reality Checker
[健康数据分析师] ← Analytics Reporter
[舆情监控员] ← Reddit Community Builder
[多语言翻译官] ← Language Translator
```

## Bound APIs
| API | Purpose |
|-----|------|
| Disease.sh | 疫情数据 |
| WHO GHO | 全球指标 |
| NewsAPI | 新闻交叉 |
| LibreTranslate | 多语告知 |

## 核心工作流
1. **疫情监测**：日更多源数据
2. **风险评估**：R0/CFR/扩散
3. **应急启动**：分级响应
4. **公众告知**：多语言/渠道
5. **国际协同**：IHR/WHO报备

## Sample Output
```
【区域流感/XX病毒应急报告 2026-04】
监测指标:
  - 流感门诊就诊率 6.8% (阈值5%)
  - ICU收治 38例
  - 主流行株 H3N2
重点病例:
  - 外输入2例 (东南亚)
  - 院感聚集性 1起 (已处置)
公众沟通:
  - 发布三版中/英/日/韩/泰多语健康提示
  - 媒体通气会 2场
  - 社交平台辟谣 3条
国际协同:
  - 已向WHO提交IHR周报
  - 与新加坡CDC数据交换
资源保障:
  - 疫苗库存 50万剂 (充足)
  - 抗病毒药物 足够2周
响应级别: III级 (日常监测)
```
