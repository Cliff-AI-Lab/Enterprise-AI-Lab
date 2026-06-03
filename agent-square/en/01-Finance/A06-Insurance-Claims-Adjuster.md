---
name: 保险定损员
name_en: Insurance Claims Adjuster
type: Composite Application
industry: Finance
composed_of: [医保理赔专员, 法律文书审查员, 评估分析]
apis: [OpenFDA, Geocoding APIs, ExchangeRate-API]
emoji: 🚗
---

# 🚗 保险定损员 Insurance Claims Adjuster

## Use Case
车险/财险/健康险线上快速定损，拍照+OCR+规则引擎。

## Agent Composition
```
[医保理赔专员] → 医疗单据审核
[法律文书审查员] → 责任归属判断
[风控合规官] → 骗保识别
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenFDA | 药品/器械合理性 |
| OpenStreetMap Nominatim | 事故地点地理编码 |
| OpenWeatherMap | 事故日天气核验 |

## 核心工作流
1. **报案受理**：照片+单据+陈述
2. **真实性核验**：时间+地点+天气
3. **定损测算**：维修/医疗/误工
4. **骗保筛查**：历史+模式识别
5. **赔付决策**：批/补资料/拒

## Sample Output
```
【车险定损 #CLM-20260417-8821】
出险时间: 4/15 22:30 上海延安高架
核验:
  ✅ 当时小雨 (气象吻合)
  ✅ 地理位置在承保范围
  ⚠️ 被保人两年内第4次事故 (风险提示)
定损金额:
  - 车辆维修 ¥18,400
  - 第三方 ¥6,200
  - 合计 ¥24,600
骗保评分: 低 (18/100)
决定: 通过, 72小时打款
```
