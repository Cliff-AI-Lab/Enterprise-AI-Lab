---
name: 宠物消费生态
name_en: Pet Consumption Ecosystem
type: Composite Application
industry: Agriculture
composed_of: [畜牧健康管理师, 电商运营专家, 患者服务助手, 社交电商运营]
source_refs: [Healthcare Customer Service, Growth Hacker, Instagram Curator]
apis: [OpenFDA Animal, Shopify, Instagram Graph, OpenFoodFacts]
emoji: 🐕
---

# 🐕 宠物消费生态 Pet Consumption Ecosystem

## Use Case
宠物食品+用品+医疗+服务全品类DTC生态, 复用亲情经济。

## Agent Composition (使用 public-apis Animals 类别)
```
[畜牧健康管理师] → 宠物健康
[电商运营专家] ← Growth Hacker
[患者服务助手] → 宠物医疗客服
[社交电商运营] ← Instagram Curator
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenFDA Animal | 宠物药品 |
| OpenFoodFacts | 宠物食品成分 |
| Shopify | DTC商店 |
| Instagram Graph | 猫狗社区 |
| The Dog API (public-apis Animals) | 品种+图片 |

## 核心工作流
1. **宠物建档**：品种+体重+健康
2. **智能推荐**：食品+用品+医疗
3. **订阅制**：粮食/保健品月送
4. **内容社区**：养宠分享
5. **线下O2O**：医院/美容

## Sample Output
```
【某宠物品牌 年度运营】
注册用户: 380万宠物主
订阅用户: 48,000 (月增8%)
年GMV: ¥2.8亿
品类:
  - 主粮 42% (订阅主力)
  - 零食/罐头 22%
  - 保健品 15%
  - 用品 12%
  - 医疗 9%
用户画像:
  - 80%养狗 | 40%养猫 | 15%养其他
  - 宠物主月花费 ¥480
  - 复购率 68% (订阅锁定)
社区:
  - 小红书"养宠"话题 5.2亿阅读
  - 品牌账号粉丝 280万
  - UGC月1.2万条
服务:
  - 合作宠物医院 4,200家
  - AI宠物健康问答 月50万次
  - 上门洗浴/寄养 覆盖28城
```
