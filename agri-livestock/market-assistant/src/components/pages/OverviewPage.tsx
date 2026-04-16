import { motion } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import { TrendingUp, TrendingDown, Minus, ShoppingCart, AlertTriangle, Bot, Database, CheckCircle2, Clock, XCircle, Brain, ArrowRight, Warehouse } from 'lucide-react'
import { COMMODITIES, type CommodityId } from '@/context/AppContext'
import { getCommodityData, getInventoryData, getAgentList } from '@/data/mockData'
import { formatPrice, formatPercent } from '@/lib/utils'
import { useApp } from '@/context/AppContext'

const si = { opacity: 0, y: 20 }
const sa = { opacity: 1, y: 0 }
const st = (i: number) => ({ delay: i * 0.06, duration: 0.4 } as const)

function CommodityCard({ id, index }: { readonly id: CommodityId; readonly index: number }) {
  const def = COMMODITIES.find(c => c.id === id)!
  const d = getCommodityData(id)
  const cc = d.coreConclusion
  const trend = cc.trendAssessment.value
  const prices = d.actualPrices.filter((v): v is number => v !== null).slice(-14)
  const { setPage } = useApp()

  const sparkOption = {
    backgroundColor: 'transparent',
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: 'category' as const, show: false, data: prices.map((_, i) => i) },
    yAxis: { type: 'value' as const, show: false, min: Math.min(...prices) * 0.998, max: Math.max(...prices) * 1.002 },
    series: [{
      type: 'line' as const, data: prices, smooth: true, symbol: 'none',
      lineStyle: { color: cc.predictedChange >= 0 ? '#10b981' : '#f43f5e', width: 2 },
      areaStyle: { color: { type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: cc.predictedChange >= 0 ? 'rgba(16,185,129,0.15)' : 'rgba(244,63,94,0.15)' },
        { offset: 1, color: 'transparent' },
      ] } },
    }],
  }

  return (
    <motion.div initial={si} animate={sa} transition={st(index)} onClick={() => setPage('analysis')}
      className="card-base p-5 cursor-pointer hover:border-neon/30 transition-all group">
      <div className="flex items-center justify-between mb-3">
        <div>
          <span className="text-xs text-text-muted uppercase tracking-widest">{def.name}</span>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="font-display text-2xl font-bold text-text-primary">{formatPrice(cc.currentPrice)}</span>
            <span className="text-xs text-text-muted">{def.unit}</span>
          </div>
        </div>
        <div className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${
          cc.predictedChange > 0.005 ? 'bg-up/10 text-up' : cc.predictedChange < -0.005 ? 'bg-down/10 text-down' : 'bg-bg-elevated text-text-muted'
        }`}>
          {cc.predictedChange > 0.005 ? <TrendingUp size={12} /> : cc.predictedChange < -0.005 ? <TrendingDown size={12} /> : <Minus size={12} />}
          {cc.predictedChange > 0 ? '+' : ''}{(cc.predictedChange * 100).toFixed(1)}%
        </div>
      </div>

      <ReactECharts option={sparkOption} style={{ height: 56 }} opts={{ renderer: 'canvas' }} />

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border-default">
        <div className="flex items-center gap-3">
          <div>
            <span className="text-[10px] text-text-muted block">看涨概率</span>
            <span className={`text-xs font-mono font-semibold ${trend > 0.6 ? 'text-up' : trend < 0.4 ? 'text-down' : 'text-warning'}`}>
              {Math.round(trend * 100)}%
            </span>
          </div>
          <div>
            <span className="text-[10px] text-text-muted block">明日预测</span>
            <span className="text-xs font-mono font-semibold text-text-secondary">{formatPrice(cc.predictedPrice)}</span>
          </div>
        </div>
        <span className="text-[10px] px-2 py-0.5 rounded bg-neon/8 text-neon">{d.procurementSummary.action}</span>
      </div>
    </motion.div>
  )
}

export default function OverviewPage() {
  const inventory = getInventoryData()
  const agents = getAgentList()
  const { setPage } = useApp()

  const dangerItems = inventory.filter(i => i.status !== 'safe')
  const running = agents.filter(a => a.status === 'running').length
  const errors = agents.filter(a => a.status === 'error').length
  const totalCalls = 393

  // Mini donut for agent status
  const agentDonut = {
    backgroundColor: 'transparent',
    series: [{
      type: 'pie' as const, radius: ['65%', '85%'], center: ['50%', '50%'],
      label: { show: false }, itemStyle: { borderColor: 'transparent', borderWidth: 2 },
      data: [
        { value: running, itemStyle: { color: '#10b981' } },
        { value: errors, itemStyle: { color: '#f43f5e' } },
        { value: agents.length - running - errors, itemStyle: { color: '#475569' } },
      ],
    }],
  }

  // Data quality bar
  const qualityData = [
    { label: '准确率', value: 94.2, color: '#10b981' },
    { label: '完整率', value: 89.5, color: '#14b8a6' },
    { label: '时效性', value: 78.3, color: '#f59e0b' },
  ]

  return (
    <div className="flex-1 p-4 overflow-y-auto">
      {/* Title */}
      <motion.div initial={si} animate={sa} transition={st(0)} className="mb-4">
        <h2 className="font-display text-xl font-bold text-text-primary">总览仪表盘</h2>
        <p className="text-xs text-text-muted mt-0.5">实时行情概览 · 系统运行状态 · 待处理事项</p>
      </motion.div>

      {/* Row 1: 5 Commodity Cards with sparklines */}
      <div className="grid grid-cols-5 gap-3 mb-4">
        {COMMODITIES.map((c, i) => <CommodityCard key={c.id} id={c.id} index={i + 1} />)}
      </div>

      {/* Row 2: System Status (3 cols) + Inventory Alert (2 cols) */}
      <div className="grid grid-cols-12 gap-3 mb-4">

        {/* Agent Status */}
        <motion.div initial={si} animate={sa} transition={st(6)} className="col-span-3 card-base p-5 cursor-pointer hover:border-neon/30" onClick={() => setPage('agent')}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-neon" />
              <span className="text-xs font-medium text-text-muted uppercase tracking-widest">智能体状态</span>
            </div>
            <ArrowRight size={14} className="text-text-muted" />
          </div>
          <div className="flex items-center gap-4">
            <div className="w-20 h-20">
              <ReactECharts option={agentDonut} style={{ height: 80, width: 80 }} opts={{ renderer: 'canvas' }} />
            </div>
            <div className="space-y-2 flex-1">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs"><CheckCircle2 size={10} className="text-up" />运行中</span>
                <span className="font-mono text-sm font-bold text-up">{running}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs"><XCircle size={10} className="text-down" />异常</span>
                <span className="font-mono text-sm font-bold text-down">{errors}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5 text-xs"><Clock size={10} className="text-text-muted" />暂停</span>
                <span className="font-mono text-sm font-bold text-text-muted">{agents.length - running - errors}</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Data Sources + Quality */}
        <motion.div initial={si} animate={sa} transition={st(7)} className="col-span-4 card-base p-5 cursor-pointer hover:border-neon/30" onClick={() => setPage('data')}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Database size={16} className="text-forecast" />
              <span className="text-xs font-medium text-text-muted uppercase tracking-widest">数据源 & 质量</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <span className="flex items-center gap-1 text-up"><CheckCircle2 size={10} />4</span>
              <span className="flex items-center gap-1 text-down"><XCircle size={10} />1</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2.5">
              {['大商所', '气象局', '船讯网', 'CBOT'].map(s => (
                <div key={s} className="flex items-center gap-2 text-xs">
                  <span className="w-1.5 h-1.5 rounded-full bg-up" />
                  <span className="text-text-secondary">{s}</span>
                  <span className="text-text-muted ml-auto">正常</span>
                </div>
              ))}
              <div className="flex items-center gap-2 text-xs">
                <span className="w-1.5 h-1.5 rounded-full bg-down" />
                <span className="text-text-secondary">卓创资讯</span>
                <span className="text-down ml-auto">超时</span>
              </div>
            </div>
            <div className="space-y-2.5">
              <span className="text-[10px] text-text-muted uppercase tracking-widest">数据质量</span>
              {qualityData.map(q => (
                <div key={q.label}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-text-secondary">{q.label}</span>
                    <span className="font-mono font-semibold" style={{ color: q.color }}>{q.value}%</span>
                  </div>
                  <div className="h-1.5 rounded-full bg-bg-elevated overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${q.value}%`, background: q.color }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>

        {/* Model + API Stats */}
        <motion.div initial={si} animate={sa} transition={st(8)} className="col-span-5 card-base p-5 cursor-pointer hover:border-neon/30" onClick={() => setPage('model')}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain size={16} className="text-neon" />
              <span className="text-xs font-medium text-text-muted uppercase tracking-widest">模型运行</span>
            </div>
            <span className="text-xs font-mono text-text-muted">今日调用 <span className="text-neon font-semibold">{totalCalls}</span> 次</span>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              { name: '融合模型', acc: '93.0%', status: '运行', calls: 168 },
              { name: '随机森林', acc: '91.0%', status: '运行', calls: 168 },
              { name: 'DeepSeek V3.1', acc: '—', status: '使用中', calls: 342 },
            ].map(m => (
              <div key={m.name} className="p-3 rounded-lg bg-bg-elevated">
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-up" />
                  <span className="text-xs font-medium text-text-primary">{m.name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-text-muted block">准确率</span>
                    <span className="font-mono text-sm font-bold text-up">{m.acc}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-text-muted block">7日调用</span>
                    <span className="font-mono text-sm font-semibold text-text-secondary">{m.calls}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Row 3: Inventory Overview + Action Items */}
      <div className="grid grid-cols-12 gap-3">

        {/* Inventory Overview */}
        <motion.div initial={si} animate={sa} transition={st(9)} className="col-span-5 card-base p-5 cursor-pointer hover:border-neon/30" onClick={() => setPage('integration')}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Warehouse size={16} className="text-recommend" />
              <span className="text-xs font-medium text-text-muted uppercase tracking-widest">库存概览</span>
            </div>
            {dangerItems.length > 0 && (
              <span className="text-xs px-2 py-0.5 rounded bg-down/10 text-down">{dangerItems.length} 品种需补货</span>
            )}
          </div>
          <div className="space-y-3">
            {inventory.map(item => {
              const pct = Math.min(item.currentDays / 20, 1)
              const barColor = item.status === 'danger' ? '#f43f5e' : item.status === 'warning' ? '#f59e0b' : '#10b981'
              return (
                <div key={item.commodityId}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-text-primary">{item.commodityName}</span>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="font-mono text-text-secondary">{formatPrice(item.currentStock)}吨</span>
                      <span className="font-mono font-semibold" style={{ color: barColor }}>{item.currentDays}天</span>
                    </div>
                  </div>
                  <div className="h-1.5 rounded-full bg-bg-elevated overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width: `${pct * 100}%`, background: barColor }} />
                  </div>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Procurement Summary */}
        <motion.div initial={si} animate={sa} transition={st(10)} className="col-span-3 card-base p-5">
          <div className="flex items-center gap-2 mb-4">
            <ShoppingCart size={16} className="text-neon" />
            <span className="text-xs font-medium text-text-muted uppercase tracking-widest">采购概要</span>
          </div>
          <div className="space-y-3">
            {COMMODITIES.map(def => {
              const d = getCommodityData(def.id)
              const ps = d.procurementSummary
              return (
                <div key={def.id} className="flex items-center justify-between p-2.5 rounded-lg bg-bg-elevated">
                  <div>
                    <span className="text-sm text-text-primary">{def.name}</span>
                    <span className="text-[10px] text-text-muted ml-2">{ps.action}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-mono text-neon">≤{formatPrice(ps.idealBuyBelow)}</span>
                    <span className="text-[10px] text-text-muted ml-1">{def.unit}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </motion.div>

        {/* Action Items */}
        <motion.div initial={si} animate={sa} transition={st(11)} className="col-span-4 card-base p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={16} className="text-warning" />
            <span className="text-xs font-medium text-text-muted uppercase tracking-widest">待处理事项</span>
            <span className="ml-auto text-xs font-mono text-text-muted">{dangerItems.length + 3} 项</span>
          </div>
          <div className="space-y-2">
            {dangerItems.map(item => (
              <div key={item.commodityId} className={`p-3 rounded-lg flex items-center gap-3 ${item.status === 'danger' ? 'bg-down/5 border border-down/15' : 'bg-warning/5 border border-warning/15'}`}>
                <Warehouse size={14} className={item.status === 'danger' ? 'text-down' : 'text-warning'} />
                <div className="flex-1 min-w-0">
                  <span className="text-sm text-text-primary">{item.commodityName} 库存{item.status === 'danger' ? '紧急' : '预警'}</span>
                  <span className={`text-xs ml-2 ${item.status === 'danger' ? 'text-down' : 'text-warning'}`}>仅剩{item.currentDays}天</span>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${item.status === 'danger' ? 'bg-down/10 text-down' : 'bg-warning/10 text-warning'}`}>
                  {item.status === 'danger' ? '紧急' : '关注'}
                </span>
              </div>
            ))}

            <div className="p-3 rounded-lg flex items-center gap-3 bg-down/5 border border-down/15">
              <Bot size={14} className="text-down" />
              <div className="flex-1"><span className="text-sm text-text-primary">数据采集Agent异常</span><span className="text-xs text-down ml-2">卓创资讯超时</span></div>
              <span className="text-xs px-2 py-0.5 rounded bg-down/10 text-down">检查</span>
            </div>

            <div className="p-3 rounded-lg flex items-center gap-3 bg-warning/5 border border-warning/15">
              <Clock size={14} className="text-warning" />
              <div className="flex-1"><span className="text-sm text-text-primary">偏差分析待审核</span><span className="text-xs text-text-muted ml-2">豆粕 04/14 +2.0%</span></div>
              <span className="text-xs px-2 py-0.5 rounded bg-warning/10 text-warning">审核</span>
            </div>

            <div className="p-3 rounded-lg flex items-center gap-3 bg-info/5 border border-info/15">
              <CheckCircle2 size={14} className="text-info" />
              <div className="flex-1"><span className="text-sm text-text-primary">USDA报告 4月20日发布</span><span className="text-xs text-text-muted ml-2">建议提前调整</span></div>
              <span className="text-xs px-2 py-0.5 rounded bg-info/10 text-info">提醒</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
