---
name: 警务辅助分析
name_en: Police Intelligence Assistant
type: Composite Application
industry: Government
composed_of: [安全威胁分析师, 舆情监控员, 法律文书审查员]
source_refs: [Threat Detection Engineer, Reddit Community Builder, Legal Document Review]
apis: [VirusTotal, NewsAPI, OpenSanctions]
emoji: 👮
---

# 👮 警务辅助分析 Police Intelligence Assistant

## Use Case
公安情报中心: 网上巡查、黑产识别、案件协查、重点人员管控辅助。

## Agent Composition
```
[安全威胁分析师] ← Threat Detection Engineer
[舆情监控员] ← Reddit Community Builder
[法律文书审查员] ← Legal Document Review
```

## Bound APIs
| API | Purpose |
|-----|------|
| VirusTotal | 恶意域名/样本 |
| OpenSanctions | 国际通缉 |
| NewsAPI | 舆情事件 |
| AbuseIPDB | 恶意IP |

## 核心工作流
1. **线索采集**：网上+报案+举报
2. **关联分析**：图数据库
3. **知识推理**：类案+法条
4. **协查推送**：跨区域
5. **合规审批**：内部审查

## Sample Output
```
【情报周报 W16 (脱敏)】
案件类型:
  - 电信诈骗 破案12起
  - 黑灰产涉网案件 破案8起
重点发现:
  1. 新型"AI换脸"诈骗团伙 (7省联动)
     - 关联域名6个 (VirusTotal已标恶意)
     - 预警潜在被害人2,400+
  2. 海外赌博平台导流
     - Telegram群组4个 (已纳入监控)
     - 初步锁定嫌疑人22名
协查:
  - 跨省12条协查线索
  - 国际通缉比中2条
典型技战法:
  - 资金流图谱 + 虚拟币追踪
  - OSINT公开情报汇聚
合规: 所有操作经审批 + 留痕
```
