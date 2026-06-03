---
name: 区块链数据分析
name_en: Blockchain Data Analyst
type: Composite Application
industry: Technology
composed_of: [加密货币顾问, 安全威胁分析师, 数据采集工程师]
source_refs: [Solidity Smart Contract Engineer, Blockchain Security Auditor, ZK Steward]
apis: [CoinGecko, Blockchain.info, Etherscan]
emoji: ⛓️
---

# ⛓️ 区块链数据分析 Blockchain Data Analyst

## Use Case
DeFi风控/反洗钱/黑客追踪/巨鲸监控等链上情报分析。

## Agent Composition
```
[加密货币顾问] ← Investment Researcher
[安全威胁分析师] ← Blockchain Security Auditor
[Solidity Smart Contract Engineer] ← engineering
[ZK Steward] ← specialized
```

## Bound APIs
| API | Purpose |
|-----|------|
| CoinGecko | 币种行情 |
| Blockchain.info | BTC链上 |
| Etherscan | 以太坊 |
| Chainalysis/自建 | 标签库 |

## 核心工作流
1. **链上事件监听**：出块/交易
2. **地址画像**：CEX/DEX/Mixer
3. **资金流图**：追踪转账
4. **合约审计**：漏洞模式
5. **情报推送**：黑客/巨鲸

## Sample Output
```
【链上情报周报 W16】
关键事件:
  1. 某DeFi协议遭闪电贷攻击
     - 损失 $18M (USDC/WETH)
     - 攻击路径: 价格预言机操纵
     - 资金流向: 经Tornado → 已提现至CEX
     - 已联动交易所冻结
  2. 巨鲸异动
     - 某地址累积 ETH +48,000 ($142M)
     - 很可能是某机构建仓
  3. NFT市场: BAYC 地板价跌 12%
风险预警:
  - 3个新发行合约存在rugpull特征
  - 2个项目代码和某已跑路合约相似度95%
合规:
  - 协助追回部分被盗资金 $3M
  - 与3家CEX建立黑名单共享
```
