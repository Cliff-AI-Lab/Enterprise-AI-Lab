---
name: AIOps平台
name_en: AIOps Platform
type: Composite Application
industry: Technology
composed_of: [云资源管理员, 数据采集工程师, AI模型评测师, 安全威胁分析师]
source_refs: [SRE, Infrastructure Maintainer, Incident Response Commander(engineering), Database Optimizer]
apis: [UptimeRobot, StatusPage, VirusTotal, ThingSpeak]
emoji: 🧠
---

# 🧠 AIOps平台 AIOps Platform

## Use Case
互联网公司SRE团队的智能运维平台: 指标+日志+链路三位一体+AI异常检测+根因定位。

## Agent Composition
```
[云资源管理员] ← Infrastructure Maintainer
[数据采集工程师] ← Data Engineer
[AI模型评测师] ← Model QA Specialist
[安全威胁分析师] ← Threat Detection Engineer
[Incident Response Commander] ← engineering
```

## Bound APIs
| API | Purpose |
|-----|------|
| UptimeRobot | 服务可用性 |
| StatusPage | 事件公告 |
| ThingSpeak | 指标数据流 |
| VirusTotal | 安全事件关联 |

## 核心工作流
1. **全链路数据**：Metrics+Logs+Traces
2. **异常检测**：时序AI模型
3. **告警压缩**：相似聚合
4. **根因定位**：拓扑+变更
5. **自愈**：预案触发

## Sample Output
```
【AIOps月度 战报】
监控对象: 服务 2,400 | 主机 12,000 | API 38,000
告警量: 日均 18万 → AI压缩后 1,800 (压缩率99%)
P0/P1事件: 本月12起
  - MTTD (平均发现时间): 47秒 (↓58%)
  - MTTR (平均修复时间): 8分钟 (↓65%)
AI准确率:
  - 异常检测准确率 94%
  - 根因定位首命中 82%
  - 误报率 3.2%
自愈占比: 45% (常见故障无人工介入)
成本: 减少SRE值班时长 40%
```
