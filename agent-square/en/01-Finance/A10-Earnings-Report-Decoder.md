---
name: 财报一键解读官
name_en: Earnings Report Decoder
type: Composite Application
industry: Finance
composed_of: [股票分析师, 财务记账员, 新闻聚合编辑]
apis: [SEC EDGAR, Financial Modeling Prep, NewsAPI]
emoji: 📊
---

# 📊 财报一键解读官 Earnings Report Decoder

## Use Case
财报季券商研究员/个人投资者用，SEC文件下载→关键指标对比→点评生成。

## Agent Composition
```
[股票分析师] → 行业对比
[财务记账员] → 会计科目解读
[新闻聚合编辑] → 管理层发言梳理
```

## Bound APIs
| API | Purpose |
|-----|------|
| SEC EDGAR | 10-K/10-Q/8-K下载 |
| FMP | 标准化财务数据 |
| NewsAPI | 电话会议新闻 |

## 核心工作流
1. **申报抓取**：10-Q当日推送
2. **指标拆解**：YoY/QoQ/Guidance
3. **beat or miss**：vs 市场一致预期
4. **管理层语气**：信心指数NLP
5. **报告输出**：5分钟解读版

## Sample Output
```
【英伟达 FY26Q1 财报解读】
结论: 🟢 BEAT
营收 $38.2B vs 预期 $36.8B (超 +3.8%)
EPS $0.68 vs 预期 $0.65 (超 +4.6%)
指引 Q2: $42B (市场 $40.2B) ✅
关键亮点:
  - 数据中心营收 $32.5B (+72% YoY)
  - 毛利率 77.8% (维持历史高位)
  - Blackwell量产顺利
管理层情绪: 乐观 (关键词"Strong demand"出现14次)
风险: 中国合规 + H20出口受限
市场反应预测: 盘后+4%~6%
```
