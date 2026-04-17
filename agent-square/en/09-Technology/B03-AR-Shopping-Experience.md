---
name: AR购物体验
name_en: AR Shopping Experience
type: Composite Application
industry: Technology
composed_of: [电商运营专家, AI模型评测师, 消费者洞察专家]
source_refs: [XR Immersive Developer, XR Interface Architect(spatial-computing), UI Designer(design)]
apis: [Mapbox AR, HuggingFace, Shopify]
emoji: 🛍️
---

# 🛍️ AR购物体验 AR Shopping Experience

## Use Case
家具/美妆/服装/眼镜品牌的AR试戴/试用, 提升线上转化率。

## Agent Composition
```
[XR Immersive Developer] ← spatial-computing
[UI Designer] ← design
[电商运营专家] ← Growth Hacker
[消费者洞察专家] ← Trend Researcher
```

## Bound APIs
| API | Purpose |
|-----|------|
| HuggingFace | 人脸/人体识别 |
| Shopify | 商品+订单 |
| WebAR SDK | 浏览器AR |

## 核心工作流
1. **3D建模**：商品扫描
2. **AR试戴/摆放**：手机/平板
3. **分享功能**：社交传播
4. **转化漏斗**：AR→加购→下单
5. **数据反馈**：尺寸/颜色喜好

## Sample Output
```
【某家具品牌 AR体验数据】
覆盖SKU: 680 (全部3D建模完毕)
AR激活:
  - 月使用 82万次
  - 人均时长 4.2分钟
转化效果:
  - AR用户 CVR 9.8% (无AR 3.2%, 3x)
  - 客单价 ¥2,400 (无AR ¥1,200)
  - 退货率 4.2% (无AR 12%, 明显降低)
功能热度:
  - 家中空间摆放 68%
  - 不同颜色切换 54%
  - 多件组合 32%
  - AR截图分享 28%
优化方向:
  - 户外场景试摆 (阳台家具)
  - 社交裂变: 朋友帮选
```
