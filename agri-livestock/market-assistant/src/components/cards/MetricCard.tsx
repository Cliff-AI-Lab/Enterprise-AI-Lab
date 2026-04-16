import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { formatPrice, formatPercent } from '@/lib/utils'

interface MetricCardProps {
  readonly label: string
  readonly value: number
  readonly unit?: string
  readonly change?: number
  readonly subLabel?: string
  readonly subValue?: string
  readonly accentColor?: 'neon' | 'forecast' | 'recommend'
  readonly delay?: number
}

export default function MetricCard({
  label, value, unit = '元/吨', change, subLabel, subValue, accentColor = 'neon', delay = 0,
}: MetricCardProps) {
  const colorMap = {
    neon: 'border-neon/30',
    forecast: 'border-forecast/30',
    recommend: 'border-recommend/30',
  }
  const dotMap = {
    neon: 'bg-neon',
    forecast: 'bg-forecast',
    recommend: 'bg-recommend',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
      className={`card-base p-5 ${colorMap[accentColor]}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className={`w-2 h-2 rounded-full ${dotMap[accentColor]}`} />
        <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">
          {label}
        </span>
      </div>

      <div className="flex items-end gap-2">
        <span className="font-display text-3xl font-bold text-text-primary tracking-tight">
          {formatPrice(value)}
        </span>
        <span className="text-sm text-text-muted mb-1">{unit}</span>
      </div>

      {change !== undefined && (
        <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${
          change > 0 ? 'text-up' : change < 0 ? 'text-down' : 'text-text-muted'
        }`}>
          {change > 0 ? <TrendingUp size={14} /> : change < 0 ? <TrendingDown size={14} /> : <Minus size={14} />}
          {change > 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {subLabel && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border-default">
          <span className="text-xs text-text-muted">{subLabel}</span>
          <span className="text-xs font-mono text-text-secondary">{subValue}</span>
        </div>
      )}
    </motion.div>
  )
}
