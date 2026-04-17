---
name: 二手书平台
name_en: Used Book Marketplace
type: Composite Application
industry: Retail
apis: [OpenLibrary, Google Books, AfterShip]
emoji: 📚
---

# 📚 二手书平台 Used Book Marketplace

## Use Case
多抓鱼/孔夫子模式: 二手书收购+估值+再卖+社群。

## Core Capabilities
- ISBN扫码估值
- 品相AI识别
- 库存周转
- 读书社群

## Bound APIs (Books类别)
| API | Purpose |
|-----|------|
| OpenLibrary | ISBN查询 |
| Google Books | 书籍元数据 |
| AfterShip | 物流 |

## Sample Output
```
【二手书平台 月度】
在售: 4.8万种图书
月收购: 12万册 | 月售出 18万册
周转: 22天
估值:
  - 新书上架平均定价 = 定价 × 25-45%
  - 畅销绝版书溢价
读者:
  - 月活 68万
  - 人均购书 2.8本/月
  - 复购率 48%
社群:
  - 书评UGC 月2.4万篇
  - 读书会在线 18场/月
环保价值:
  - 年减纸耗 1,400吨
  - 相当 24,000棵树
```
