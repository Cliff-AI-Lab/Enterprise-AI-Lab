import { motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Clock, ChevronRight } from 'lucide-react'
import type { DeviationEvent } from '@/data/mockData'
import { formatDate, formatPercent } from '@/lib/utils'

interface Props {
  readonly events: DeviationEvent[]
  readonly onSelect: (id: string) => void
  readonly selectedId?: string | null
}

const levelConfig = {
  ALERT: { color: 'text-down', bg: 'bg-down/10', dot: 'bg-down alert-pulse' },
  WARNING: { color: 'text-warning', bg: 'bg-warning/10', dot: 'bg-warning neon-pulse' },
  NOTICE: { color: 'text-info', bg: 'bg-info/10', dot: 'bg-info' },
}
const statusConfig = {
  confirmed: { icon: CheckCircle2, label: '已确认', color: 'text-up' },
  pending: { icon: Clock, label: '待审核', color: 'text-warning' },
  rejected: { icon: AlertTriangle, label: '已驳回', color: 'text-down' },
}

export default function DeviationList({ events, onSelect, selectedId }: Props) {
  const sorted = [...events].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.4 }} className="card-base p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">偏差事件</span>
        <span className="text-xs font-mono text-text-muted">近30天: {events.length}件</span>
      </div>
      <div className="space-y-1 flex-1 overflow-y-auto max-h-[400px]">
        {sorted.map((ev) => {
          const lc = levelConfig[ev.level]
          const sc = statusConfig[ev.feedbackStatus]
          const StatusIcon = sc.icon
          return (
            <button key={ev.id} onClick={() => onSelect(ev.id)} className={`w-full text-left p-3 rounded-lg transition-all cursor-pointer ${selectedId === ev.id ? 'bg-bg-elevated border border-border-accent' : 'hover:bg-bg-hover border border-transparent'}`}>
              <div className="flex items-start gap-3">
                <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${lc.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-mono font-semibold text-text-primary">{formatDate(ev.date)}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${lc.bg} ${lc.color}`}>{ev.level}</span>
                    {ev.appliedToModel && <span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up">已回流</span>}
                  </div>
                  <div className="text-xs text-text-secondary mb-1.5">
                    实际 <span className="font-mono text-actual">{ev.actual.toLocaleString()}</span> vs 预测 <span className="font-mono text-forecast">{ev.predicted.toLocaleString()}</span>
                    <span className={`ml-2 font-semibold ${ev.actual > ev.predicted ? 'text-up' : 'text-down'}`}>{ev.actual > ev.predicted ? '+' : ''}{formatPercent(ev.deviationRate)}</span>
                  </div>
                  <p className="text-xs text-text-muted truncate">{ev.aiAnalysis.causes[0]?.factor}{ev.manualSupplement && ' + 人工补录'}</p>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <StatusIcon size={12} className={sc.color} />
                  <ChevronRight size={14} className="text-text-muted" />
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </motion.div>
  )
}
