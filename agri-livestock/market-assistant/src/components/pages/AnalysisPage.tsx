import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, ShoppingCart, AlertTriangle, Zap, Sparkles } from 'lucide-react'
import { COMMODITIES, type CommodityId } from '@/context/AppContext'
import { getCommodityData } from '@/data/mockData'
import CollapsibleSection from '@/components/shared/CollapsibleSection'
import ThreeLineChart from '@/components/charts/ThreeLineChart'
import DeviationDetail from '@/components/deviation/DeviationDetail'
import ManualSupplement from '@/components/deviation/ManualSupplement'
import AiChatPanel from '@/components/ai/AiChatPanel'
import { formatPrice, formatPercent } from '@/lib/utils'
import RatingStars from '@/components/cards/RatingStars'

export default function AnalysisPage() {
  const [commodity, setCommodity] = useState<CommodityId>('doupo')
  const [selectedDeviation, setSelectedDeviation] = useState<string | null>(null)
  const [supplementTarget, setSupplementTarget] = useState<string | null>(null)

  const def = COMMODITIES.find(c => c.id === commodity)!
  const data = getCommodityData(commodity)
  const cc = data.coreConclusion
  const ps = data.procurementSummary

  return (
    <div className="flex-1 p-4 overflow-y-auto ">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-xl font-bold text-text-primary mb-1">行情分析</h2>
            <p className="text-xs text-text-muted">品种深度分析 + 采购建议</p>
          </div>
          {/* 品种选择Tabs */}
          <div className="flex rounded-lg border border-border-default overflow-hidden">
            {COMMODITIES.map(c => (
              <button key={c.id} onClick={() => { setCommodity(c.id); setSelectedDeviation(null) }}
                className={`px-4 py-2 text-sm transition-colors ${commodity === c.id ? 'bg-neon text-text-inverse font-medium' : 'bg-bg-card text-text-secondary hover:text-text-primary'}`}>
                {c.name}
              </button>
            ))}
          </div>
        </div>

        {/* 核心指标摘要行 */}
        <div className="grid grid-cols-4 gap-3 mb-4">
          <div className="card-base p-4">
            <span className="text-[10px] text-text-muted uppercase tracking-widest block mb-1">当前价格</span>
            <span className="font-display text-xl font-bold text-text-primary">{formatPrice(cc.currentPrice)}</span>
            <span className="text-xs text-text-muted ml-1">{def.unit}</span>
          </div>
          <div className="card-base p-4">
            <span className="text-[10px] text-text-muted uppercase tracking-widest block mb-1">明日预测</span>
            <span className="font-display text-xl font-bold text-forecast">{formatPrice(cc.predictedPrice)}</span>
            <span className={`text-xs ml-2 ${cc.predictedChange >= 0 ? 'text-up' : 'text-down'}`}>{cc.predictedChange >= 0 ? '+' : ''}{formatPercent(cc.predictedChange)}</span>
          </div>
          <div className="card-base p-4">
            <span className="text-[10px] text-text-muted uppercase tracking-widest block mb-1">看涨概率</span>
            <span className={`font-display text-xl font-bold ${cc.trendAssessment.value > 0.6 ? 'text-up' : cc.trendAssessment.value < 0.4 ? 'text-down' : 'text-warning'}`}>{Math.round(cc.trendAssessment.value * 100)}%</span>
          </div>
          <div className="card-base p-4">
            <span className="text-[10px] text-text-muted uppercase tracking-widest block mb-1">采购评级</span>
            <RatingStars rating={cc.actionRating} />
            <span className="text-xs text-text-muted mt-1 block">{ps.action}</span>
          </div>
        </div>

        {/* 折叠面板 */}
        <CollapsibleSection title={`${def.name} — 三线预测走势`} icon={<TrendingUp size={14} />}
          badge={<span className="text-xs text-text-muted">预测区间 {formatPrice(cc.priceRange.lower)}-{formatPrice(cc.priceRange.upper)}</span>} defaultOpen>
          <ThreeLineChart data={data} commodityName={def.name} onDeviationClick={setSelectedDeviation} />
        </CollapsibleSection>

        <CollapsibleSection title="采购建议详情" icon={<ShoppingCart size={14} />}
          badge={<span className={`text-xs px-1.5 py-0.5 rounded ${ps.urgency >= 4 ? 'bg-down/10 text-down' : ps.urgency >= 3 ? 'bg-warning/10 text-warning' : 'bg-up/10 text-up'}`}>{ps.action} · 紧急度{ps.urgency}/5</span>}>
          <div className="grid grid-cols-3 gap-3 mb-4">
            <div className="p-3 rounded bg-bg-elevated text-center">
              <span className="text-[10px] text-text-muted block mb-1">理想采购价</span>
              <span className="font-mono text-lg font-bold text-recommend">≤{formatPrice(ps.idealBuyBelow)}</span>
            </div>
            <div className="p-3 rounded bg-bg-elevated text-center">
              <span className="text-[10px] text-text-muted block mb-1">可接受区间</span>
              <span className="font-mono text-lg font-bold text-text-primary">{formatPrice(ps.acceptableRange[0])}-{formatPrice(ps.acceptableRange[1])}</span>
            </div>
            <div className="p-3 rounded bg-bg-elevated text-center">
              <span className="text-[10px] text-text-muted block mb-1">预警线</span>
              <span className="font-mono text-lg font-bold text-down">&gt;{formatPrice(ps.alertPrice)}</span>
            </div>
          </div>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-1.5 text-xs">
              <span className="text-text-muted">30天采购进度</span>
              <span className="font-mono text-text-secondary">{formatPrice(ps.alreadySecured)}/{formatPrice(ps.totalDemand30d)}吨 ({Math.round(ps.alreadySecured / ps.totalDemand30d * 100)}%)</span>
            </div>
            <div className="h-2 rounded-full bg-bg-elevated overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-recommend to-neon" style={{ width: `${ps.alreadySecured / ps.totalDemand30d * 100}%` }} />
            </div>
          </div>
          <div className="space-y-1.5 mb-4">
            {ps.remainingPlan.map((p, i) => (
              <div key={i} className="flex items-center gap-2 p-2.5 rounded bg-bg-elevated text-xs">
                <ShoppingCart size={11} className="text-recommend" />
                <span className="text-text-secondary flex-1">{p.trigger}</span>
                <span className="font-mono font-semibold text-text-primary">{p.volume.toLocaleString()}吨</span>
                {p.note && <span className="text-warning">{p.note}</span>}
              </div>
            ))}
          </div>
          <p className="text-xs text-text-muted p-3 rounded bg-bg-elevated border-l-2 border-recommend">{ps.strategyDetail}</p>
        </CollapsibleSection>

        <CollapsibleSection title="偏差分析 & 归因" icon={<AlertTriangle size={14} />}
          badge={<span className="text-xs text-text-muted">{data.deviationEvents.length} 个事件</span>}>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              {[...data.deviationEvents].sort((a, b) => b.date.localeCompare(a.date)).map(ev => (
                <button key={ev.id} onClick={() => setSelectedDeviation(ev.id)}
                  className={`w-full text-left p-3 rounded transition-all ${selectedDeviation === ev.id ? 'bg-bg-elevated border border-border-accent' : 'bg-bg-elevated border border-transparent hover:border-border-default'}`}>
                  <div className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full ${ev.level === 'WARNING' ? 'bg-warning' : 'bg-info'}`} />
                    <span className="font-mono text-text-primary">{ev.date}</span>
                    <span className={`text-xs px-1 rounded ${ev.level === 'WARNING' ? 'bg-warning/10 text-warning' : 'bg-info/10 text-info'}`}>{ev.level}</span>
                    <span className={`text-xs ml-auto font-mono ${ev.actual > ev.predicted ? 'text-up' : 'text-down'}`}>{ev.actual > ev.predicted ? '+' : ''}{formatPercent(ev.deviationRate)}</span>
                  </div>
                  <p className="text-xs text-text-muted mt-1 truncate">{ev.aiAnalysis.causes[0]?.factor}</p>
                </button>
              ))}
            </div>
            <div>
              {selectedDeviation
                ? <DeviationDetail events={data.deviationEvents} deviationId={selectedDeviation} onClose={() => setSelectedDeviation(null)} onOpenSupplement={setSupplementTarget} />
                : <div className="h-full flex items-center justify-center text-xs text-text-muted">点击左侧事件查看详情</div>}
            </div>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="驱动因子分析" icon={<Zap size={14} />}>
          <div className="space-y-2">
            {data.driverFactors.map((f, i) => (
              <div key={f.name} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated">
                <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-neon text-text-inverse' : 'bg-bg-primary text-text-muted'}`}>{i + 1}</span>
                <span className="text-sm text-text-primary flex-1">{f.name}</span>
                <span className="text-xs text-text-muted">{f.category}</span>
                <span className="text-xs text-text-muted w-48 truncate">{f.change}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${f.direction === 'bullish' ? 'bg-up/10 text-up' : 'bg-down/10 text-down'}`}>{f.direction === 'bullish' ? '看涨' : '看跌'}</span>
                <div className="w-20 h-1.5 rounded-full bg-bg-primary"><div className={`h-full rounded-full ${f.direction === 'bullish' ? 'bg-neon' : 'bg-down'}`} style={{ width: `${f.weight * 100}%` }} /></div>
                <span className="text-xs font-mono text-text-muted w-8 text-right">{Math.round(f.weight * 100)}%</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="AI 对话分析" icon={<Sparkles size={14} />}>
          <AiChatPanel commodityName={def.name} commodityData={data} />
        </CollapsibleSection>

        <ManualSupplement deviationId={supplementTarget} onClose={() => setSupplementTarget(null)} />
      </motion.div>
    </div>
  )
}
