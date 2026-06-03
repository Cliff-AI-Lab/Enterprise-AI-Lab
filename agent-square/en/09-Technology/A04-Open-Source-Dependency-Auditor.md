---
name: 开源依赖审计
name_en: Open Source Dependency Auditor
type: Composite Application
industry: Technology
composed_of: [API集成工程师, 安全威胁分析师, 法律文书审查员]
source_refs: [Code Reviewer, Security Engineer, Git Workflow Master]
apis: [GitHub API, OSV (Open Source Vulnerabilities), Libraries.io]
emoji: 📦
---

# 📦 开源依赖审计 Open Source Dependency Auditor

## Use Case
DevSecOps: 扫描项目依赖的CVE、许可证合规、供应链攻击风险。

## Agent Composition
```
[API集成工程师] ← Code Reviewer (engineering)
[安全威胁分析师] ← Security Engineer
[法律文书审查员] → 许可证审查
[Git Workflow Master] ← engineering
```

## Bound APIs
| API | Purpose |
|-----|------|
| GitHub API | 代码库扫描 |
| OSV | 漏洞数据库 |
| Libraries.io | 包元数据 |
| npm/PyPI | 包版本 |

## 核心工作流
1. **SBOM生成**：依赖清单
2. **CVE扫描**：已知漏洞
3. **许可证**：GPL/MIT/Apache冲突
4. **供应链风险**：typo-squatting
5. **修复建议**：升级/替换/补丁

## Sample Output
```
【某后端服务 依赖审计】
SBOM: 1,840个直接 + 间接依赖
风险清单:
  🔴 高危 CVE 3:
     - log4j 2.14.1 CVE-2021-44228 (logshell)
       → 升级至 2.17.1 (建议) ✅
     - jackson 2.13 反序列化
     - Spring 5.3 SpEL注入
  🟠 中危 CVE 28
  🟡 低危 CVE 120
许可证问题:
  - GPL v3 依赖 1项 (商业软件风险)
    建议: 替换为 Apache-2.0 替代库
供应链:
  - 1个疑似 typo-squatting 包 (已拦截)
  - 2个长期无人维护包 (考虑替代)
CI拦截策略:
  - 严重CVE阻断合并
  - 每周自动升级PR
```
