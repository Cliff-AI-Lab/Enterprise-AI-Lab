import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import type { DriverFactor } from '@/data/mockData'

interface Props { readonly factors: DriverFactor[] }

export default function DriverCard({ factors }: Props) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.5, ease: [0.16, 1, 0.3, 1] }} className="card-base p-5">
      <div className="flex items-center gap-2 mb-4">
        <Zap size={16} className="text-warning" />
        <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">Top 驱动因子</span>
      </div>
      <div className="space-y-3">
        {factors.map((f, i) => (
          <div key={f.name} className="flex items-start gap-3">
            <span className={`w-5 h-5 rounded flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 ${i === 0 ? 'bg-neon text-text-inverse' : 'bg-bg-elevated text-text-muted'}`}>{i + 1}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-text-primary truncate">{f.name}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${f.direction === 'bullish' ? 'bg-up/10 text-up' : 'bg-down/10 text-down'}`}>{f.direction === 'bullish' ? '↑涨' : '↓跌'}</span>
              </div>
              <p className="text-xs text-text-muted mt-0.5 truncate">{f.change}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <div className="w-16 h-1.5 rounded-full bg-bg-elevated overflow-hidden">
                <div className={`h-full rounded-full ${f.direction === 'bullish' ? 'bg-neon' : 'bg-down'}`} style={{ width: `${f.weight * 100}%` }} />
              </div>
              <span className="text-xs font-mono text-text-muted w-8 text-right">{Math.round(f.weight * 100)}%</span>
            </div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}
