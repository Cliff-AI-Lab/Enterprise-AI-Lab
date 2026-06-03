---
name: 供应链金融专员
name_en: Supply Chain Finance Specialist
type: Composite Application
industry: Finance
composed_of: [贷款评估师, 供应链策略师, 应付账款专员, 关务报关员]
apis: [OpenCorporates, AfterShip, ExchangeRate-API]
emoji: 🔗
---

# 🔗 供应链金融专员 Supply Chain Finance Specialist

## Use Case
核心企业+上下游供应商的应收账款保理、反向保理、订单融资。

## Agent Composition
```
[供应链策略师] → 供应商画像与等级
[贷款评估师] → 授信额度
[应付账款专员] → 应付账单核验
[关务报关员] → 跨境订单货权确认
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenCorporates | 核心企业+供应商关联 |
| AfterShip | 在途货物货权 |
| ExchangeRate-API | 跨境结算 |

## 核心工作流
1. **供应链地图**：核心+1级+2级
2. **订单/发票确权**：核心企业背书
3. **额度测算**：应收账款×折扣率
4. **放款**：T+1到账
5. **回款清算**：到期核心企业付款

## Sample Output
```
【核心企业A 供应商融资池 月报】
上游供应商: 186家 (在池 124家)
月度融资笔数: 412笔 | 合计 ¥3.8亿
平均账期: 65天 → 提前回款
利率: 年化 5.8% (LPR+约200BP)
不良率: 0.12% (行业0.5%) ✅
典型案例:
  - 供应商B 订单¥320万, 48小时到账¥282万 (折扣88%)
新增接入: 3家2级供应商
```
