---
name: 中小企业贷款风控
name_en: SME Credit Risk Engine
type: Composite Application
industry: Finance
composed_of: [贷款评估师, 财务记账员, 风控合规官, 销售数据分析师]
apis: [OpenCorporates, SEC EDGAR, Treasury.gov]
emoji: 🏦
---

# 🏦 中小企业贷款风控 SME Credit Risk Engine

## Use Case
为银行/助贷平台/供应链金融的小微企业授信模型，整合工商、税务、发票、流水做综合评分。

## Agent Composition
```
[风控合规官] → 企业合规筛查
[贷款评估师] → 授信额度+利率定价
[财务记账员] → 流水/报表解析
[销售数据分析师] → 营收真实性交叉验证
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenCorporates | 工商/股东信息 |
| SEC EDGAR (US上市公司) | 供应商披露 |
| Treasury.gov | 基准利率 |
| ExchangeRate-API | 外币业务折算 |

## 核心工作流
1. **主体画像**：工商+法定代表人+关联企业
2. **经营验证**：发票+流水+纳税
3. **信用评分**：A/B/C/D + 分数0-1000
4. **额度定价**：公式 + 风险溢价
5. **放款监控**：贷后行为画像

## Sample Output
```
【小微企业授信评估 - 上海某制造商】
主体: 核心企业二级供应商
年营收: ¥3,200万 (发票核实)
经营年限: 7年 | 稳定付款核心1家
评分: B+ (728/1000)
维度拆解:
  - 工商/法律: 90/100
  - 财务健康: 75/100
  - 经营稳定性: 72/100
  - 行业景气: 65/100
建议:
  - 授信额度: ¥400万 (保守建议¥320万)
  - 利率: LPR+120BP = 4.45%
  - 期限: 12个月, 按月付息
  - 风险点: 前五大客户集中度75%, 需分散
```
