---
name: 美妆品牌孵化
name_en: Beauty Brand Incubator
type: Composite Application
industry: Retail
composed_of: [品牌出海顾问, 社交电商运营, 消费者洞察专家, 商品定价分析师]
source_refs: [Brand Guardian, UI Designer, Image Prompt Engineer, Visual Storyteller(design), Xiaohongshu Specialist, Weibo Strategist, Zhihu Strategist(marketing)]
apis: [OpenFoodFacts, Instagram Graph, TikTok, Open Prices]
emoji: 💄
---

# 💄 美妆品牌孵化 Beauty Brand Incubator

## Use Case
新锐美妆品牌的0→1孵化: 概念→配方→视觉→内容→渠道→复购。

## Agent Composition (榨取 design 多个Agent)
```
[Brand Guardian] ← design
[UI Designer] ← design
[Image Prompt Engineer] ← design
[Visual Storyteller] ← design
[Xiaohongshu Specialist] ← marketing
[Weibo Strategist] ← marketing
[Zhihu Strategist] ← marketing
[消费者洞察专家] ← Trend Researcher
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenFoodFacts | 成分透明数据 |
| Instagram Graph | 视觉营销 |
| TikTok Display | 短视频 |
| Open Prices | 竞品定价 |

## 核心工作流
1. **概念定位**：目标人群+痛点
2. **配方/产品**：代工厂合作
3. **视觉体系**：VI/包装/官网
4. **内容矩阵**：小红书+抖音+知乎
5. **投放+复购**：DTC闭环

## Sample Output
```
【新锐纯净美妆品牌 M12复盘】
品类: 抗老精华+面膜
核心客群: 25-35岁职场女性
孵化里程碑:
  M1-3: 配方 + 视觉 + 内测
  M4-6: 小红书200篇KOC种草
  M7-9: 抖音+Tmall双渠道启动
  M10-12: DTC独立站+复购体系
M12数据:
  - 累计GMV ¥2,800万
  - 用户数 48,000
  - 复购率 34%
  - NPS 62
  - 毛利率 58%
品牌印记:
  - 成分党高分: 小红书种草博主背书
  - 视觉"极简高级" 被模仿
  - 明星使用曝光2次 (自然)
下阶段: 品类扩张(面霜) + 出海东南亚
```
