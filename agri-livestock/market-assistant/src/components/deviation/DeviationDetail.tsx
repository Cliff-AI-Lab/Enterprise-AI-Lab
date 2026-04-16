import { motion, AnimatePresence } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import { X, Brain, UserPen, ArrowUpRight, ArrowDownRight, CheckCircle2, Clock } from 'lucide-react'
import type { DeviationEvent } from '@/data/mockData'
import { formatPercent } from '@/lib/utils'
import RatingStars from '@/components/cards/RatingStars'

interface Props {
  readonly events: DeviationEvent[]
  readonly deviationId: string | null
  readonly onClose: () => void
  readonly onOpenSupplement: (id: string) => void
}

function CauseChart({ causes }: { readonly causes: DeviationEvent['aiAnalysis']['causes'] }) {
  const option = {
    backgroundColor: 'transparent', animation: true, animationDuration: 800,
    grid: { left: 110, right: 40, top: 8, bottom: 8 },
    xAxis: { type: 'value' as const, max: 100, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { show: false }, splitLine: { show: false } },
    yAxis: { type: 'category' as const, data: causes.map(c => c.factor).reverse(), axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#94a3b8', fontSize: 11, fontFamily: 'Inter' } },
    series: [{ type: 'bar' as const, data: causes.map(c => ({ value: Math.round(c.contribution * 100), itemStyle: { color: c.direction === 'bullish' ? '#14b8a6' : '#f43f5e', borderRadius: [0, 3, 3, 0] } })).reverse(), barWidth: 16, label: { show: true, position: 'right' as const, formatter: '{c}%', color: '#94a3b8', fontFamily: 'JetBrains Mono', fontSize: 11 } }],
  }
  return <ReactECharts option={option} style={{ height: 100 }} opts={{ renderer: 'canvas' }} />
}

export default function DeviationDetail({ events, deviationId, onClose, onOpenSupplement }: Props) {
  const ev = events.find(e => e.id === deviationId)

  return (
    <AnimatePresence>
      {ev && (
        <motion.div key={ev.id} initial={{ opacity: 0, x: 40 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 40 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} className="card-base p-5 border-border-accent">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-sm font-display font-bold text-text-primary">偏差归因分析</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${ev.level === 'WARNING' ? 'bg-warning/10 text-warning' : 'bg-info/10 text-info'}`}>{ev.level}</span>
              </div>
              <p className="text-xs text-text-muted font-mono">{ev.date} | {ev.id}</p>
            </div>
            <button onClick={onClose} className="p-1 rounded hover:bg-bg-hover text-text-muted"><X size={16} /></button>
          </div>

          <div className="flex gap-4 mb-4 p-3 rounded-lg bg-bg-elevated">
            <div className="flex-1"><span className="text-xs text-text-muted block mb-0.5">实际价</span><span className="font-display text-xl font-bold text-actual">{ev.actual.toLocaleString()}</span></div>
            <div className="flex-1"><span className="text-xs text-text-muted block mb-0.5">预测价</span><span className="font-display text-xl font-bold text-forecast">{ev.predicted.toLocaleString()}</span></div>
            <div className="flex-1"><span className="text-xs text-text-muted block mb-0.5">偏差率</span><span className={`font-display text-xl font-bold ${ev.actual > ev.predicted ? 'text-up' : 'text-down'}`}>{ev.actual > ev.predicted ? '+' : ''}{formatPercent(ev.deviationRate)}</span></div>
          </div>

          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2"><Brain size={14} className="text-forecast" /><span className="text-xs font-medium text-text-secondary uppercase tracking-widest">AI 归因分析</span></div>
            <CauseChart causes={ev.aiAnalysis.causes} />
            <div className="mt-3 p-3 rounded-lg bg-bg-elevated border-l-2 border-forecast">
              <p className="text-xs text-text-secondary leading-relaxed"><strong className="text-text-primary">因果链：</strong>{ev.aiAnalysis.summary}</p>
              <p className="text-xs text-text-muted mt-2 leading-relaxed"><strong className="text-warning">后续影响：</strong>{ev.aiAnalysis.futureImpact}</p>
            </div>
          </div>

          {ev.manualSupplement ? (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2"><UserPen size={14} className="text-neon" /><span className="text-xs font-medium text-text-secondary uppercase tracking-widest">人工补录</span></div>
              <div className="p-3 rounded-lg bg-bg-elevated border-l-2 border-neon">
                <div className="flex items-center justify-between mb-2"><span className="text-xs text-text-muted">{ev.manualSupplement.submittedBy}</span><span className="text-xs px-1.5 py-0.5 rounded bg-neon/10 text-neon">{ev.manualSupplement.category}</span></div>
                <p className="text-xs text-text-secondary leading-relaxed mb-2">{ev.manualSupplement.description}</p>
                <div className="flex items-center gap-4 text-xs text-text-muted">
                  <span className="flex items-center gap-1">{ev.manualSupplement.impactDirection === 'up' ? <ArrowUpRight size={12} className="text-up" /> : <ArrowDownRight size={12} className="text-down" />}{ev.manualSupplement.impactMagnitude}元/吨</span>
                  <span>可信度: <RatingStars rating={ev.manualSupplement.credibility} /></span>
                </div>
              </div>
            </div>
          ) : (
            <button onClick={() => onOpenSupplement(ev.id)} className="w-full mb-4 p-3 rounded-lg border border-dashed border-border-default hover:border-neon/50 hover:bg-bg-hover transition-all text-sm text-text-muted hover:text-neon flex items-center justify-center gap-2"><UserPen size={14} />补充人工分析信息</button>
          )}

          <div className="flex items-center justify-between pt-3 border-t border-border-default">
            <div className="flex items-center gap-2 text-xs">
              {ev.feedbackStatus === 'confirmed' ? <CheckCircle2 size={12} className="text-up" /> : <Clock size={12} className="text-warning" />}
              <span className="text-text-muted">{ev.feedbackStatus === 'confirmed' ? '已确认' : '待审核'}</span>
              {ev.appliedToModel && <span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up ml-2">已回流模型</span>}
            </div>
            {ev.feedbackStatus === 'pending' && (
              <div className="flex gap-2">
                <button className="px-3 py-1 rounded text-xs bg-up/10 text-up hover:bg-up/20">确认</button>
                <button className="px-3 py-1 rounded text-xs bg-down/10 text-down hover:bg-down/20">驳回</button>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
