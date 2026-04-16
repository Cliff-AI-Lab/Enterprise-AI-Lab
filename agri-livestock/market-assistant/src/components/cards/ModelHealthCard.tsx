import { motion } from 'framer-motion'
import { Shield, RefreshCw } from 'lucide-react'
import { formatPercent } from '@/lib/utils'

interface Props {
  readonly data: { accuracy: number; mape: number; feedbackAdoption: number; version: string; lastRetrain: string }
}

export default function ModelHealthCard({ data }: Props) {
  const metrics = [
    { label: '预测准确率', value: formatPercent(data.accuracy), status: (data.accuracy > 0.85 ? 'good' : data.accuracy > 0.7 ? 'warn' : 'bad') as 'good' | 'warn' | 'bad' },
    { label: '平均偏差率', value: formatPercent(data.mape), status: (data.mape < 0.05 ? 'good' : data.mape < 0.1 ? 'warn' : 'bad') as 'good' | 'warn' | 'bad' },
    { label: '反馈采纳率', value: formatPercent(data.feedbackAdoption), status: (data.feedbackAdoption > 0.8 ? 'good' : 'warn') as 'good' | 'warn' | 'bad' },
  ]
  const statusColor = { good: 'bg-up', warn: 'bg-warning', bad: 'bg-down' }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3, ease: [0.16, 1, 0.3, 1] }} className="card-base p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-neon" />
          <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">模型健康度</span>
        </div>
        <span className="text-xs font-mono text-text-muted">{data.version}</span>
      </div>
      <div className="space-y-3">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center justify-between">
            <span className="text-sm text-text-secondary">{m.label}</span>
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono font-semibold text-text-primary">{m.value}</span>
              <span className={`w-2 h-2 rounded-full ${statusColor[m.status]}`} />
            </div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border-default text-xs text-text-muted">
        <RefreshCw size={12} />最近重训: {data.lastRetrain}
      </div>
    </motion.div>
  )
}
