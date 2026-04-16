import { motion } from 'framer-motion'
import { ShoppingCart, Target, AlertTriangle, ChevronRight } from 'lucide-react'
import { formatPrice } from '@/lib/utils'
import RatingStars from '@/components/cards/RatingStars'
import type { CommodityDataSet } from '@/data/mockData'

interface Props {
  readonly data: CommodityDataSet['procurementSummary']
  readonly unit: string
}

export default function ProcurementPanel({ data: ps, unit }: Props) {
  const securedPercent = Math.round((ps.alreadySecured / ps.totalDemand30d) * 100)

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.5 }} className="card-base p-5">
      <div className="flex items-center gap-2 mb-4">
        <ShoppingCart size={16} className="text-recommend" />
        <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">采购建议</span>
      </div>

      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-display text-lg font-bold text-recommend">{ps.action}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${ps.urgency >= 4 ? 'bg-down/10 text-down' : ps.urgency >= 3 ? 'bg-warning/10 text-warning' : 'bg-up/10 text-up'}`}>紧急度 {ps.urgency}/5</span>
          </div>
          <RatingStars rating={ps.rating} />
        </div>
        <div className="text-right">
          <span className="text-xs text-text-muted block">今日建议量</span>
          <span className="font-display text-xl font-bold text-text-primary">{ps.todaySuggested}<span className="text-sm text-text-muted ml-1">吨</span></span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-4">
        <div className="p-2 rounded-lg bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">理想采购价</span>
          <span className="font-mono text-xs font-semibold text-recommend">≤{formatPrice(ps.idealBuyBelow)}</span>
        </div>
        <div className="p-2 rounded-lg bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">可接受区间</span>
          <span className="font-mono text-xs font-semibold text-text-primary">{formatPrice(ps.acceptableRange[0])}-{formatPrice(ps.acceptableRange[1])}</span>
        </div>
        <div className="p-2 rounded-lg bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">预警线</span>
          <span className="font-mono text-xs font-semibold text-down">&gt;{formatPrice(ps.alertPrice)}</span>
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs text-text-muted">30天采购进度</span>
          <span className="text-xs font-mono text-text-secondary">{formatPrice(ps.alreadySecured)}/{formatPrice(ps.totalDemand30d)}吨</span>
        </div>
        <div className="h-2 rounded-full bg-bg-elevated overflow-hidden">
          <motion.div initial={{ width: 0 }} animate={{ width: `${securedPercent}%` }} transition={{ duration: 1, delay: 0.8 }} className="h-full rounded-full bg-gradient-to-r from-recommend to-neon" />
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs font-mono text-recommend">{securedPercent}%</span>
          <span className="text-xs text-text-muted">剩余 {formatPrice(ps.totalDemand30d - ps.alreadySecured)}吨</span>
        </div>
      </div>

      <div className="mb-4">
        <span className="text-xs text-text-secondary mb-2 block uppercase tracking-widest">分批计划</span>
        <div className="space-y-2">
          {ps.remainingPlan.map((plan, i) => (
            <div key={i} className="flex items-center gap-2 p-2 rounded bg-bg-elevated text-xs">
              <Target size={12} className="text-recommend shrink-0" />
              <span className="text-text-secondary flex-1">{plan.trigger}</span>
              <span className="font-mono font-semibold text-text-primary shrink-0 text-xs">{plan.volume.toLocaleString()}吨</span>
              {plan.note && <span className="text-warning flex items-center gap-0.5 text-[10px] shrink-0"><AlertTriangle size={9} />{plan.note}</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="p-3 rounded-lg bg-bg-elevated border-l-2 border-recommend">
        <p className="text-xs text-text-secondary leading-relaxed">{ps.strategyDetail}</p>
      </div>

      <div className="flex gap-2 mt-4">
        <button className="flex-1 py-2 rounded-lg bg-recommend/10 text-recommend text-xs font-medium hover:bg-recommend/20 transition-colors flex items-center justify-center gap-1">生成采购报告<ChevronRight size={14} /></button>
        <button className="flex-1 py-2 rounded-lg bg-neon text-text-inverse text-xs font-semibold hover:brightness-110 transition-all flex items-center justify-center gap-1">一键下单<ChevronRight size={14} /></button>
      </div>
    </motion.div>
  )
}
