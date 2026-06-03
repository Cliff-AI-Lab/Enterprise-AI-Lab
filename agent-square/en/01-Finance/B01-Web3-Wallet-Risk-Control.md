---
name: Web3钱包风控
name_en: Web3 Wallet Risk Control
type: Composite Application
industry: Finance
composed_of: [加密货币顾问, 区块链数据分析, 安全威胁分析师]
source_refs: [Blockchain Security Auditor, ZK Steward, Solidity Smart Contract Engineer, Agentic Identity & Trust Architect]
apis: [CoinGecko, Etherscan, VirusTotal, URLhaus]
emoji: 🔐
---

# 🔐 Web3钱包风控 Web3 Wallet Risk Control

## Use Case
Web3钱包/交易所(MetaMask/Coinbase/Binance)前置风控: 诈骗合约识别、授权审计、钓鱼网站拦截。

## Agent Composition
```
[Blockchain Security Auditor] ← specialized
[ZK Steward] ← specialized
[Solidity Smart Contract Engineer] ← engineering
[Agentic Identity & Trust Architect] ← specialized
```

## Bound APIs
| API | Purpose |
|-----|------|
| Etherscan | 合约验证 |
| CoinGecko | 币种真伪 |
| VirusTotal + URLhaus | 钓鱼域名 |

## 核心工作流
1. **交易前检测**：合约地址扫描
2. **签名风险**：授权范围解析
3. **钓鱼拦截**：domain黑名单
4. **空投鉴定**：Free币真假
5. **异常行为**：资产异动告警

## Sample Output
```
【Web3钱包风控月报】
月活钱包: 48万 | 月交易 820万笔
拦截数据:
  ⚠️ 拦截诈骗合约交互 2,800次
  ⚠️ 高危授权警告 12,400次 (infinite approval)
  ⚠️ 钓鱼网站访问拦截 6,200次
  ⚠️ 假空投/rugpull代币 1,200个
用户损失:
  - 已挽回 $18M (24小时内撤销)
  - 未挽回 $2.4M (主要硬件钱包)
教育:
  - 推送风险提醒 48万条
  - 用户风险知识测试参与率 22%
合规:
  - 与Chainalysis数据共享
  - 配合执法部门 12起案件
```
