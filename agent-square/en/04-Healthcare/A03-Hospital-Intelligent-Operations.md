---
name: 医院智能运营
name_en: Hospital Intelligent Operations
type: Composite Application
industry: Healthcare
composed_of: [患者服务助手, 健康数据分析师, 医保理赔专员, 生产排程员]
source_refs: [Healthcare Customer Service, Analytics Reporter, Legal Document Review]
apis: [Healthcare.gov, NPPES, CMS, QuickChart]
emoji: 🏨
---

# 🏨 医院智能运营 Hospital Intelligent Operations

## Use Case
大型医院信息科: 患者流、DRG病组、医保结算、人力排班一体化。

## Agent Composition
```
[患者服务助手] ← Hospitality Guest Services (specialized)
[健康数据分析师] ← Analytics Reporter (support)
[医保理赔专员] ← Legal Document Review
[生产排程员] → 改造成"医护排班"
```

## Bound APIs
| API | Purpose |
|-----|------|
| NPPES NPI | 医师资质 |
| CMS APIs | DRG分组 |
| Healthcare.gov | 保险计划 |
| QuickChart | 运营大屏 |

## 核心工作流
1. **患者流**：门诊/入院/手术/出院
2. **DRG分析**：病组成本vs 收入
3. **医保盈亏**：次均费用 vs 支付
4. **医护排班**：供需匹配
5. **指标大屏**：实时呈现

## Sample Output
```
【某三甲医院 运营月报 2026-04】
门诊: 38万人次 | 住院 1.8万人次
手术台次: 4,600 (利用率92%)
DRG盈亏 Top5 (亏损):
  - IR23 胃肠腔镜 亏 ¥1,800/例 ← 耗材偏高
  - FM33 心脏起搏 亏 ¥9,200/例 ← 设备高
  - ... 改善方向: 集采+路径
DRG盈利 Top5:
  - QU21 (X光诊断) +¥1,800
  - OJ13 (新生儿) +¥2,400
整体医保结算: 结余 ¥820万 (率1.8%)
医护排班:
  - 急诊排班 满足率 98%
  - 专家出诊 次数 +5%
预警:
  - ICU床位周转偏慢, 影响周转
  - 某科室医生过劳, 需轮休
```
