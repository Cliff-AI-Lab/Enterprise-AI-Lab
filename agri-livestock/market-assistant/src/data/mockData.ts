// ═══════════════════════════════════════════
// 行情分析智能助手 — Mock 数据层 V2
// 多品种数据生成器 + 库存/采购记录/智能体
// ═══════════════════════════════════════════

import type { CommodityId, CommodityDef } from '@/context/AppContext'
import { COMMODITIES } from '@/context/AppContext'

// ─── 日期工具 ───
function genDates(startStr: string, count: number): string[] {
  const dates: string[] = []
  const start = new Date(startStr)
  for (let i = 0; i < count; i++) {
    const d = new Date(start)
    d.setDate(d.getDate() + i)
    dates.push(d.toISOString().slice(0, 10))
  }
  return dates
}

// 固定种子伪随机 (让同品种每次生成相同数据)
function seededRandom(seed: number) {
  let s = seed
  return () => { s = (s * 16807 + 0) % 2147483647; return s / 2147483647 }
}

const TODAY = '2026-04-15'
const HISTORY_START = '2026-03-16'
const historyDates = genDates(HISTORY_START, 31)
const futureDates = genDates('2026-04-16', 30)
export const allDates = [...historyDates, ...futureDates]
export const todayIndex = historyDates.length - 1

// ─── 接口定义 ───
export interface ProcurementPoint {
  date: string; idealPrice: number; acceptableLower: number; acceptableUpper: number
  stopLoss: number; action: string; urgency: number; volume: number | null
}

export interface DeviationEvent {
  id: string; date: string; predicted: number; actual: number; deviationRate: number
  level: 'NOTICE' | 'WARNING' | 'ALERT'
  aiAnalysis: { causes: { factor: string; contribution: number; direction: 'bullish' | 'bearish' }[]; summary: string; futureImpact: string }
  manualSupplement?: { submittedBy: string; category: string; description: string; impactDirection: 'up' | 'down'; impactMagnitude: number; credibility: number }
  feedbackStatus: 'pending' | 'confirmed' | 'rejected'; appliedToModel: boolean
}

export interface DriverFactor {
  name: string; category: string; change: string; direction: 'bullish' | 'bearish'; weight: number
}

export interface CommodityDataSet {
  actualPrices: (number | null)[]
  forecastPrices: number[]
  confidenceIntervals: { ci80: [number, number]; ci95: [number, number] }[]
  procurementData: ProcurementPoint[]
  deviationEvents: DeviationEvent[]
  driverFactors: DriverFactor[]
  modelHealth: { accuracy: number; mape: number; feedbackAdoption: number; version: string; lastRetrain: string }
  coreConclusion: {
    trendAssessment: { value: number; change: number }; priceRange: { lower: number; upper: number; confidence: number }
    actionRating: number; currentPrice: number; predictedPrice: number; predictedChange: number
  }
  procurementSummary: {
    action: string; urgency: number; rating: number; idealBuyBelow: number; acceptableRange: [number, number]
    alertPrice: number; totalDemand30d: number; alreadySecured: number; todaySuggested: number
    remainingPlan: { trigger: string; volume: number; note?: string }[]; strategyDetail: string
  }
}

// ─── 每品种驱动因子模板 ───
const driverTemplates: Record<CommodityId, DriverFactor[]> = {
  doupo: [
    { name: '巴西港口拥堵指数', category: '供应链', change: '延误7天→22天(+214%)', direction: 'bullish', weight: 0.35 },
    { name: 'CBOT大豆净多头持仓', category: '金融端', change: '基金增持+12万手', direction: 'bullish', weight: 0.28 },
    { name: '美湾至中国海运费率', category: '供应链', change: '报$58/吨(年内新高)', direction: 'bullish', weight: 0.18 },
    { name: '人民币汇率', category: '宏观', change: '贬值至7.28(年内新低)', direction: 'bullish', weight: 0.15 },
    { name: '豆粕-菜粕价差', category: '替代品', change: '缩窄至-420元/吨', direction: 'bearish', weight: 0.10 },
  ],
  yumi: [
    { name: '东北产区天气', category: '供应链', change: '春播延迟5-7天', direction: 'bullish', weight: 0.30 },
    { name: '深加工企业开机率', category: '需求端', change: '提升至68%(+5%)', direction: 'bullish', weight: 0.25 },
    { name: '北方港口库存', category: '供应链', change: '降至380万吨(-12%)', direction: 'bullish', weight: 0.20 },
    { name: '进口玉米到港', category: '供应链', change: '4月预计120万吨', direction: 'bearish', weight: 0.15 },
    { name: '小麦替代比例', category: '替代品', change: '饲料配方中降至8%', direction: 'bullish', weight: 0.10 },
  ],
  caipo: [
    { name: '两湖地区菜籽收购', category: '供应链', change: '新季菜籽上市推迟', direction: 'bullish', weight: 0.30 },
    { name: '水产养殖需求', category: '需求端', change: '开塘率同比+15%', direction: 'bullish', weight: 0.25 },
    { name: '加拿大菜籽进口', category: '供应链', change: '关税政策不确定', direction: 'bullish', weight: 0.20 },
    { name: '豆粕-菜粕价差', category: '替代品', change: '扩大至420元/吨', direction: 'bearish', weight: 0.15 },
    { name: '沿海油厂菜粕库存', category: '供应链', change: '降至2.1万吨(-30%)', direction: 'bullish', weight: 0.10 },
  ],
  yufen: [
    { name: '秘鲁捕鱼季配额', category: '供应链', change: '同比缩减20%', direction: 'bullish', weight: 0.35 },
    { name: '国内水产料需求', category: '需求端', change: '旺季启动提前', direction: 'bullish', weight: 0.25 },
    { name: '港口鱼粉库存', category: '供应链', change: '降至8万吨(历史低位)', direction: 'bullish', weight: 0.20 },
    { name: '人民币汇率', category: '宏观', change: '贬值推高进口成本', direction: 'bullish', weight: 0.10 },
    { name: '肉骨粉替代', category: '替代品', change: '价差收窄至800元', direction: 'bearish', weight: 0.10 },
  ],
  douyou: [
    { name: '国内大豆压榨量', category: '供应链', change: '周度210万吨(+8%)', direction: 'bearish', weight: 0.30 },
    { name: '棕榈油进口成本', category: '替代品', change: '印尼出口关税上调', direction: 'bullish', weight: 0.25 },
    { name: '餐饮消费恢复', category: '需求端', change: '五一备货需求启动', direction: 'bullish', weight: 0.20 },
    { name: '商业库存', category: '供应链', change: '降至95万吨(-10%)', direction: 'bullish', weight: 0.15 },
    { name: '生物柴油政策', category: '政策', change: 'B10掺混目标推进', direction: 'bullish', weight: 0.10 },
  ],
}

// ─── 偏差事件模板 ───
const deviationTemplates: Record<CommodityId, DeviationEvent[]> = {
  doupo: [
    { id: 'DEV-DP-001', date: '2026-03-25', predicted: 4840, actual: 4855, deviationRate: 0.031, level: 'WARNING',
      aiAnalysis: { causes: [{ factor: '港口拥堵加剧', contribution: 0.45, direction: 'bullish' }, { factor: 'CBOT多头增持', contribution: 0.30, direction: 'bullish' }, { factor: '汇率贬值', contribution: 0.15, direction: 'bullish' }], summary: '巴西港口拥堵指数升至22天，带动短期供应预期收紧。', futureImpact: '若拥堵持续至月底，上行压力继续。' }, feedbackStatus: 'confirmed', appliedToModel: true },
    { id: 'DEV-DP-002', date: '2026-04-05', predicted: 5000, actual: 5040, deviationRate: 0.008, level: 'NOTICE',
      aiAnalysis: { causes: [{ factor: '期现价差扩大', contribution: 0.50, direction: 'bullish' }, { factor: '下游备货需求', contribution: 0.35, direction: 'bullish' }], summary: '期现价差拉大触发贸易商惜售。', futureImpact: '短期偏差可控。' }, feedbackStatus: 'confirmed', appliedToModel: false },
    { id: 'DEV-DP-003', date: '2026-04-11', predicted: 5030, actual: 5120, deviationRate: 0.049, level: 'WARNING',
      aiAnalysis: { causes: [{ factor: '巴西南部暴雨持续', contribution: 0.45, direction: 'bullish' }, { factor: '美湾海运费率飙升', contribution: 0.30, direction: 'bullish' }, { factor: '期货多头加仓', contribution: 0.20, direction: 'bullish' }], summary: '巴西暴雨→港口延迟→到港推后2周→供应缺口→现货报价抬升。', futureImpact: '若暴雨持续至月底：上行200-300元/吨。' },
      manualSupplement: { submittedBy: '张三（采购经理）', category: '行业信息', description: '某大型油厂突然停机检修，区域供应骤降，预计停机2周。', impactDirection: 'up', impactMagnitude: 150, credibility: 4 }, feedbackStatus: 'confirmed', appliedToModel: true },
    { id: 'DEV-DP-004', date: '2026-04-14', predicted: 5050, actual: 5040, deviationRate: 0.020, level: 'NOTICE',
      aiAnalysis: { causes: [{ factor: '菜粕替代效应增强', contribution: 0.55, direction: 'bearish' }, { factor: '油厂逐步复产', contribution: 0.30, direction: 'bearish' }], summary: '豆粕-菜粕价差收窄，部分饲料厂启动配方替代。', futureImpact: '替代效应可能抑制上涨。' }, feedbackStatus: 'pending', appliedToModel: false },
  ],
  yumi: [
    { id: 'DEV-YM-001', date: '2026-03-28', predicted: 2780, actual: 2810, deviationRate: 0.011, level: 'NOTICE',
      aiAnalysis: { causes: [{ factor: '东北农户惜售', contribution: 0.50, direction: 'bullish' }, { factor: '深加工补库', contribution: 0.30, direction: 'bullish' }], summary: '东北余粮减少叠加深加工企业补库需求。', futureImpact: '短期支撑偏强。' }, feedbackStatus: 'confirmed', appliedToModel: true },
    { id: 'DEV-YM-002', date: '2026-04-10', predicted: 2840, actual: 2870, deviationRate: 0.035, level: 'WARNING',
      aiAnalysis: { causes: [{ factor: '春播延迟预期', contribution: 0.45, direction: 'bullish' }, { factor: '港口库存降低', contribution: 0.35, direction: 'bullish' }], summary: '春播推迟引发新季减产担忧。', futureImpact: '若天气持续不利，看涨情绪加强。' }, feedbackStatus: 'confirmed', appliedToModel: true },
  ],
  caipo: [
    { id: 'DEV-CP-001', date: '2026-04-03', predicted: 3180, actual: 3220, deviationRate: 0.013, level: 'NOTICE',
      aiAnalysis: { causes: [{ factor: '水产开塘提前', contribution: 0.55, direction: 'bullish' }, { factor: '菜籽到港减少', contribution: 0.30, direction: 'bullish' }], summary: '水产养殖旺季提前启动拉动菜粕需求。', futureImpact: '5月前需求支撑价格。' }, feedbackStatus: 'confirmed', appliedToModel: true },
  ],
  yufen: [
    { id: 'DEV-YF-001', date: '2026-04-08', predicted: 12600, actual: 12900, deviationRate: 0.024, level: 'WARNING',
      aiAnalysis: { causes: [{ factor: '秘鲁配额缩减', contribution: 0.50, direction: 'bullish' }, { factor: '港口库存新低', contribution: 0.35, direction: 'bullish' }], summary: '秘鲁新季配额同比减少20%，港口库存降至历史低位。', futureImpact: '短期内供应偏紧格局难改。' }, feedbackStatus: 'confirmed', appliedToModel: true },
  ],
  douyou: [
    { id: 'DEV-DY-001', date: '2026-04-06', predicted: 8180, actual: 8250, deviationRate: 0.009, level: 'NOTICE',
      aiAnalysis: { causes: [{ factor: '棕榈油进口成本上行', contribution: 0.45, direction: 'bullish' }, { factor: '五一备货启动', contribution: 0.35, direction: 'bullish' }], summary: '印尼棕榈油出口关税上调，推升替代品价格。', futureImpact: '节前需求支撑价格。' }, feedbackStatus: 'confirmed', appliedToModel: false },
  ],
}

// ─── 品种价格序列生成 ───
function genPriceSeries(def: CommodityDef) {
  const rng = seededRandom(def.basePrice)
  const base = def.basePrice
  const vol = def.volatility
  const actual: number[] = []
  let p = base * (0.94 + rng() * 0.02)
  for (let i = 0; i < 31; i++) {
    p += (rng() - 0.45) * 20 * vol
    actual.push(Math.round(p))
  }
  const forecast: number[] = []
  let fp = base * (0.935 + rng() * 0.02)
  for (let i = 0; i < 61; i++) {
    fp += (rng() - 0.45) * 18 * vol
    forecast.push(Math.round(fp))
  }
  return { actual, forecast }
}

function genCI(prices: number[], startWiden: number, vol: number) {
  const rng = seededRandom(prices[0] ?? 1000)
  return prices.map((p, i) => {
    const spread = (i < startWiden ? 40 : 40 + (i - startWiden) * 6) * vol + rng() * 15
    return {
      ci80: [Math.round(p - spread * 0.8), Math.round(p + spread * 0.8)] as [number, number],
      ci95: [Math.round(p - spread), Math.round(p + spread)] as [number, number],
    }
  })
}

// ─── 主函数：按品种获取全部数据 ───
const cache = new Map<CommodityId, CommodityDataSet>()

export function getCommodityData(commodityId: CommodityId): CommodityDataSet {
  if (cache.has(commodityId)) return cache.get(commodityId)!

  const def = COMMODITIES.find(c => c.id === commodityId)!
  const { actual, forecast } = genPriceSeries(def)
  const currentPrice = actual[actual.length - 1]
  const predictedPrice = forecast[31]
  const ci = genCI(forecast, todayIndex, def.volatility)

  const procData: ProcurementPoint[] = futureDates.map((date, i) => {
    const b = forecast[31 + i]
    const lower = b - Math.round(60 * def.volatility)
    const upper = b + Math.round(40 * def.volatility)
    const actions = ['分批采购', '分批采购', '观望', '立即采购', '观望']
    return { date, idealPrice: lower + 20, acceptableLower: lower, acceptableUpper: upper,
      stopLoss: b + Math.round(150 * def.volatility),
      action: i < 3 ? '分批采购' : i < 7 ? '观望' : actions[i % 5],
      urgency: i < 3 ? 4 : i < 7 ? 2 : 3,
      volume: i < 3 ? Math.round(500 * def.volatility) : i < 7 ? null : Math.round(300 * def.volatility),
    }
  })

  const demand = Math.round(5000 * def.volatility)
  const secured = Math.round(demand * 0.3)

  const ds: CommodityDataSet = {
    actualPrices: [...actual, ...Array(30).fill(null)],
    forecastPrices: forecast,
    confidenceIntervals: ci,
    procurementData: procData,
    deviationEvents: deviationTemplates[commodityId] ?? [],
    driverFactors: driverTemplates[commodityId] ?? [],
    modelHealth: { accuracy: 0.85 + Math.random() * 0.08, mape: 0.02 + Math.random() * 0.03, feedbackAdoption: 0.8 + Math.random() * 0.1, version: 'v2.3.1', lastRetrain: '2026-04-14' },
    coreConclusion: {
      trendAssessment: { value: 0.55 + Math.random() * 0.3, change: -0.05 + Math.random() * 0.2 },
      priceRange: { lower: Math.round(currentPrice * 0.96), upper: Math.round(currentPrice * 1.04), confidence: 0.88 + Math.random() * 0.08 },
      actionRating: Math.ceil(Math.random() * 2) + 2,
      currentPrice, predictedPrice,
      predictedChange: (predictedPrice - currentPrice) / currentPrice,
    },
    procurementSummary: {
      action: '分批采购', urgency: 3, rating: 4,
      idealBuyBelow: Math.round(currentPrice * 0.97),
      acceptableRange: [Math.round(currentPrice * 0.96), Math.round(currentPrice * 0.99)],
      alertPrice: Math.round(currentPrice * 1.04),
      totalDemand30d: demand, alreadySecured: secured,
      todaySuggested: Math.round(demand * 0.1),
      remainingPlan: [
        { trigger: `价格回落至${Math.round(currentPrice * 0.96)}以下`, volume: Math.round(demand * 0.2) },
        { trigger: '每下跌50元', volume: Math.round(demand * 0.1) },
        { trigger: '4月25日前未触发', volume: demand - secured - Math.round(demand * 0.3), note: '按需补仓' },
      ],
      strategyDetail: `当前${def.name}价格处于预测区间中位，建议分批采购锁定需求量，关注回调窗口。`,
    },
  }

  cache.set(commodityId, ds)
  return ds
}

// ─── 库存数据 ───
export interface InventoryItem {
  commodityId: CommodityId
  commodityName: string
  currentStock: number          // 当前库存（吨）
  safetyDays: number            // 安全库存天数
  dailyConsumption: number      // 日均消耗（吨）
  currentDays: number           // 当前可用天数
  trend30d: number[]            // 近30天库存变化
  status: 'safe' | 'warning' | 'danger'
}

export function getInventoryData(): InventoryItem[] {
  return COMMODITIES.map(def => {
    const daily = Math.round(80 * def.volatility + 20)
    const stock = Math.round(daily * (4 + Math.random() * 16))
    const days = Math.round(stock / daily)
    const trend: number[] = []
    let t = stock + daily * 15
    for (let i = 0; i < 30; i++) {
      t -= daily * (0.8 + Math.random() * 0.4)
      if (i % 7 === 3) t += daily * (3 + Math.random() * 4) // 补货日
      trend.push(Math.round(Math.max(t, daily * 2)))
    }
    return {
      commodityId: def.id, commodityName: def.name,
      currentStock: stock, safetyDays: 7, dailyConsumption: daily, currentDays: days,
      trend30d: trend,
      status: days < 5 ? 'danger' : days < 7 ? 'warning' : 'safe',
    }
  })
}

// ─── 历史采购记录 ───
export interface PurchaseRecord {
  id: string; date: string; commodity: string; quantity: number; unitPrice: number
  totalAmount: number; supplier: string; status: '已完成' | '运输中' | '待确认'
}

const suppliers = ['中粮贸易', '益海嘉里', '九三集团', '大北农', '正大集团', '嘉吉中国', '邦基三维', '路易达孚']

export function getPurchaseHistory(): PurchaseRecord[] {
  const records: PurchaseRecord[] = []
  const dates = genDates('2026-01-05', 100)
  let id = 1
  for (const def of COMMODITIES) {
    const rng = seededRandom(def.basePrice + 777)
    for (let i = 0; i < 12; i++) {
      const qty = Math.round((200 + rng() * 800) * def.volatility)
      const price = Math.round(def.basePrice * (0.95 + rng() * 0.1))
      const dateIdx = Math.floor(rng() * dates.length)
      records.push({
        id: `PO-2026-${String(id++).padStart(4, '0')}`,
        date: dates[dateIdx],
        commodity: def.name,
        quantity: qty,
        unitPrice: price,
        totalAmount: qty * price,
        supplier: suppliers[Math.floor(rng() * suppliers.length)],
        status: i < 9 ? '已完成' : i < 11 ? '运输中' : '待确认',
      })
    }
  }
  return records.sort((a, b) => b.date.localeCompare(a.date))
}

// ─── 智能体数据 ───
export interface AgentInfo {
  id: string; name: string; description: string
  status: 'running' | 'paused' | 'error'
  enabled: boolean
  lastRun: string; successRate: number; runCount24h: number
  logs: { time: string; level: 'info' | 'warn' | 'error'; message: string }[]
}

export function getAgentList(): AgentInfo[] {
  return [
    { id: 'agent-forecast', name: '行情预测 Agent', description: 'SARIMA+随机森林混合模型，每日自动生成30天价格预测',
      status: 'running', enabled: true, lastRun: '2026-04-15 08:00', successRate: 0.97, runCount24h: 24,
      logs: [
        { time: '08:00', level: 'info', message: '豆粕预测任务完成，MAPE=3.1%' },
        { time: '08:02', level: 'info', message: '玉米预测任务完成，MAPE=2.8%' },
        { time: '08:05', level: 'info', message: '菜粕预测任务完成，MAPE=3.5%' },
        { time: '08:07', level: 'warn', message: '鱼粉模型置信度偏低(82%)，建议人工复核' },
      ] },
    { id: 'agent-deviation', name: '偏差分析 Agent', description: '实时监控预测vs实际偏差，自动触发归因分析',
      status: 'running', enabled: true, lastRun: '2026-04-15 09:30', successRate: 0.94, runCount24h: 48,
      logs: [
        { time: '09:30', level: 'info', message: '检测到豆粕偏差+4.9%，已触发归因分析' },
        { time: '09:31', level: 'info', message: '归因报告已生成，主因：巴西暴雨(45%)' },
        { time: '09:32', level: 'info', message: '已推送采购经理审核' },
      ] },
    { id: 'agent-procure', name: '采购推荐 Agent', description: '结合预测、库存、需求计划生成最优采购策略',
      status: 'running', enabled: true, lastRun: '2026-04-15 07:30', successRate: 0.91, runCount24h: 12,
      logs: [
        { time: '07:30', level: 'info', message: '今日采购建议已生成：豆粕500吨@≤4850' },
        { time: '07:31', level: 'warn', message: '鱼粉库存不足5天，建议紧急采购' },
        { time: '07:32', level: 'info', message: '玉米库存充足，建议观望' },
      ] },
    { id: 'agent-collect', name: '数据采集 Agent', description: '定时采集商情平台、大商所、卓创资讯等数据源',
      status: 'error', enabled: true, lastRun: '2026-04-15 06:00', successRate: 0.85, runCount24h: 144,
      logs: [
        { time: '06:00', level: 'info', message: '大商所期货数据采集完成(23条)' },
        { time: '06:01', level: 'error', message: '卓创资讯接口超时(3次重试失败)' },
        { time: '06:02', level: 'info', message: '船讯网物流数据采集完成' },
        { time: '06:05', level: 'warn', message: '商情平台数据延迟15分钟' },
      ] },
  ]
}

// ─── AI 默认消息 ───
export const defaultAiMessages = [
  { role: 'assistant' as const, content: '根据最新分析，巴西暴雨影响正在减弱，港口效率预计本周恢复。建议维持分批采购策略，关注回调窗口。', time: '09:30' },
  { role: 'assistant' as const, content: '库存提醒：鱼粉库存仅剩4.8天，低于7天安全线，建议尽快安排补货。', time: '10:15' },
]
