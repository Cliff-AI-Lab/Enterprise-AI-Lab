---
name: DTC专科诊所
name_en: DTC Specialty Clinic
type: Composite Application
industry: Healthcare
composed_of: [患者服务助手, 药物信息查询员, 电商运营专家]
source_refs: [Healthcare Customer Service, Growth Hacker]
apis: [Healthcare.gov, Shopify, LibreTranslate]
emoji: 🏥
---

# 🏥 DTC专科诊所 DTC Specialty Clinic

## Use Case
消费医疗(脱发/减肥/抗衰)的DTC运营: 线上问诊+用药+复诊+随访订阅。

## Agent Composition
```
[患者服务助手] ← Hospitality Guest Services
[药物信息查询员] ← Healthcare Customer Service
[电商运营专家] ← Growth Hacker (marketing)
```

## Bound APIs
| API | Purpose |
|-----|------|
| Shopify | 处方/非处方商城 |
| OpenFDA | 药品信息 |
| LibreTranslate | 国际服务 |
| Stripe (via FX-API) | 支付 |

## 核心工作流
1. **线上问诊**：表单+视频
2. **开方+药品**：医生+药师双审
3. **订阅配送**：月度/季度
4. **随访管理**：疗效追踪
5. **复购激活**：个性化推荐

## Sample Output
```
【某减肥DTC 月度运营】
订阅用户: 34,200 (↑18% MoM)
ARR: $12M
指标:
  - 首方CVR: 8.2%
  - 6月留存: 54%
  - NPS: 62
业务:
  - GLP-1处方: 28,400份
  - 营养补充: 12,800单
  - 健身课程: 4,600单
合规风控:
  - 开方审核率 100%
  - 退货率 3.2% (行业5%)
  - 投诉 0.18% (监管阈值1%) ✅
增长实验:
  - A/B: "体重-10磅保证" 落地页 +24%CVR
  - 达人合作 ROI 4.8x
```
