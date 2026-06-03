---
name: ABS资产证券化
name_en: ABS Structurer
type: Composite Application
industry: Finance
apis: [SEC EDGAR, Treasury.gov]
emoji: 📑
---

# 📑 ABS资产证券化

## Use Case
ABS/CMBS/CLO发行的资产池分析+结构设计+评级对接。

## Core Capabilities
- 底层资产现金流建模
- 分层结构设计(优先/劣后)
- 评级机构对接
- 信息披露

## Bound APIs
- **SEC EDGAR**: ABS注册声明
- **Treasury**: 基准利率

## Sample Output
```
【某消费贷ABS 发行准备】
资产池: ¥30亿 | 加权收益率 18%
结构:
  - 优先A: ¥21亿 AAA 利率 3.2%
  - 优先B: ¥6亿 AA+ 利率 4.5%
  - 次级: ¥3亿 (发起人持有)
超额利差: 6.5% | 预期损失 3.8%
```
