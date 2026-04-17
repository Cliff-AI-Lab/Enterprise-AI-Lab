---
name: 渔业远洋捕捞
name_en: Deep-Sea Fishery Ops
type: Composite Application
industry: Agriculture
composed_of: [水产养殖管家, 运力调度员, 关务报关员, 环境监测员]
source_refs: [Fleet Dispatcher, Legal Compliance Checker, Geographer]
apis: [OpenWeatherMap, NASA POWER, OpenRouteService, RestCountries]
emoji: 🎣
---

# 🎣 渔业远洋捕捞 Deep-Sea Fishery Ops

## Use Case
远洋渔船队的渔场搜寻+作业调度+跨国合规+冷链回运。

## Agent Composition
```
[水产养殖管家] → 海洋环境
[运力调度员] → 船队调度
[关务报关员] ← Legal Compliance Checker
[环境监测员] ← Reality Checker
```

## Bound APIs
| API | Purpose |
|-----|------|
| OpenWeatherMap | 海况/风浪 |
| NASA POWER | 海温/洋流 |
| RestCountries | 公海/专属经济区 |
| OpenRouteService | 航线 |

## 核心工作流
1. **渔场探测**：海温+叶绿素+洋流
2. **船队部署**：多船协同
3. **配额管理**：RFMO规则
4. **证书**：CCAMLR/IUU合规
5. **冷链回运**：港口分拨

## Sample Output
```
【某远洋船队 太平洋金枪鱼 季度报告】
船队: 28艘 (围网18 + 延绳10)
作业海域: 中西太平洋 (WCPO)
当季产量: 12,800吨 (金枪鱼)
  - 鲣鱼 9,200吨 | 大目 2,400吨 | 黄鳍 1,200吨
配额: 14,000吨 (WCPFC分配, 使用91%) ✅
环境监测:
  - SST: 28-30℃ (利于鲣鱼聚集)
  - 叶绿素浓度 高值区锁定作业
IUU合规:
  - AIS全程开启
  - 观察员覆盖 20% 船次
  - 证书齐全, 无违规记录
冷链:
  - -60℃ 超低温冷藏
  - 卸港: 日本清水+台湾高雄+上海
价格:
  - 鲣鱼 $1,500/吨 (罐头原料)
  - 大目 $10,000/吨 (刺身级)
季度毛利: $800万
```
