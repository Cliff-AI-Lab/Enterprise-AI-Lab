---
name: 货运保险定损
name_en: Cargo Insurance Adjuster
type: Composite Application
industry: Logistics
composed_of: [包裹追踪员, 法律文书审查员, 关务报关员, 安全威胁分析师]
source_refs: [Evidence Collector, Legal Document Review]
apis: [AfterShip, OpenWeatherMap, VirusTotal]
emoji: 🚛
---

# 🚛 货运保险定损 Cargo Insurance Adjuster

## Use Case
国内/国际货运险的快速定损+骗保识别+理赔打款。

## Agent Composition
```
[包裹追踪员] ← Evidence Collector
[法律文书审查员] ← Legal Document Review
[关务报关员] ← Legal Compliance Checker
[安全威胁分析师] → 骗保风控
```

## Bound APIs
| API | Purpose |
|-----|------|
| AfterShip | 物流节点 |
| OpenWeatherMap | 天气核验 |
| VirusTotal | 单证真伪辅助 |

## 核心工作流
1. **报案受理**：单号+损失
2. **轨迹核验**：物流节点
3. **损失评估**：照片+发票
4. **骗保筛查**：历史+模式
5. **赔付**：银行对接

## Sample Output
```
【货运险定损月报】
受案: 2,840单 | 已赔付 2,620 | 拒赔 180 | 调查中 40
总赔款: ¥4,200万
原因分布:
  - 破损 42%
  - 丢失 18%
  - 水湿 12%
  - 盗抢 8%
  - 其他 20%
骗保识别:
  - 高风险案件 38起
  - 已查实欺诈 12起 (涉案¥380万)
  - 查实率 32%
理赔时效:
  - 平均周期 3.8天
  - 简易案件 T+1 打款
合规:
  - 保险监管要求全达标
  - 客户满意度 88%
```
