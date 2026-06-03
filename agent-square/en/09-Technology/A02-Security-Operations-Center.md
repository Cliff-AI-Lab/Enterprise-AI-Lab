---
name: 安全运营中心(SOC)
name_en: Security Operations Center
type: Composite Application
industry: Technology
composed_of: [安全威胁分析师, 云资源管理员, 法律文书审查员]
source_refs: [Threat Detection Engineer, Security Engineer, Blockchain Security Auditor, Agentic Identity & Trust Architect]
apis: [VirusTotal, AbuseIPDB, Shodan, URLhaus]
emoji: 🛡️
---

# 🛡️ 安全运营中心(SOC) Security Operations Center

## Use Case
企业SOC: SIEM+SOAR+威胁情报+红蓝对抗一体化运营。

## Agent Composition
```
[安全威胁分析师] ← Threat Detection Engineer
[云资源管理员] ← Infrastructure Maintainer
[法律文书审查员] → 合规报告
[Security Engineer] ← engineering
[Blockchain Security Auditor] ← specialized
```

## Bound APIs
| API | Purpose |
|-----|------|
| VirusTotal | 文件/URL/IP |
| AbuseIPDB | IP滥用 |
| Shodan | 暴露面扫描 |
| URLhaus | 恶意URL |
| HIBP | 数据泄露查询 |

## 核心工作流
1. **日志收敛**：SIEM聚合
2. **规则+AI双检**：已知+未知威胁
3. **SOAR自动化**：剧本响应
4. **威胁狩猎**：主动
5. **事件复盘**：红蓝对抗

## Sample Output
```
【SOC周报 W16】
日均日志量: 12TB
告警:
  - Level4 (严重): 2 → 均已处置
  - Level3 (高): 18 → 100%处置
  - Level2 (中): 240 → SLA 4h达成98%
重大事件:
  1. 某员工邮箱疑遭钓鱼登录
     - MFA阻断成功 ✅
     - 已强制改密+全网排查
  2. 外部扫描源 500+ 自动封堵
威胁情报对接:
  - 本周新增IOC 8,400条
  - 命中公司资产 3次 (已处置)
红蓝对抗:
  - 本周演练: 攻击路径8条, 防御发现6条
  - 改善项5条 已入backlog
合规:
  - 等保三级自检: 3项需整改
  - SOC 2 Type II审计 准备中
```
