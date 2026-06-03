---
name: 奢侈品二手
name_en: Luxury Resale Marketplace
type: Composite Application
industry: Retail
composed_of: [质量检测员, 客服智能助手, 风控合规官, 物品定价分析师]
source_refs: [Evidence Collector, Brand Guardian, Legal Document Review]
apis: [OpenSanctions, Shopify, Instagram Graph, HuggingFace]
emoji: 👜
---

# 👜 奢侈品二手 Luxury Resale Marketplace

## Use Case
奢侈品二手交易平台(如Vestiaire/红布林): AI鉴定+定价+寄售+社区。

## Agent Composition
```
[质量检测员] ← Evidence Collector
[Brand Guardian] ← design
[风控合规官] ← Legal Document Review
[商品定价分析师] ← Financial Analyst
```

## Bound APIs
| API | Purpose |
|-----|------|
| Shopify | 商城 |
| Instagram | 种草 |
| HuggingFace | 图像鉴定模型 |

## 核心工作流
1. **卖家寄售**：物流+安全
2. **AI鉴定**：真伪+成色
3. **人工复核**：资深鉴定师
4. **定价建议**：市场+成色
5. **成交+售后**：退换/包换

## Sample Output
```
【某奢侈品二手 月度运营】
寄售SKU: 18,000件 | 成交 3,400件
月GMV: ¥2.8亿
均件价: ¥8,200
品类TOP:
  - 手袋 48% (爱马仕/香奈儿主导)
  - 腕表 22% (劳/百达/欧米茄)
  - 服装 15%
  - 配饰 10%
  - 其他 5%
鉴定:
  - AI鉴定首通率 78%
  - 人工复核通过 98%
  - 拒收率 3.2% (仿品/不符合)
平台费:
  - 卖家 15% (寄售)
  - 买家 3% 服务费
  - 品牌溢价 回收30-50%
风控:
  - 0 起假货投诉
  - 退货率 5.2%
  - 客户NPS 68
```
