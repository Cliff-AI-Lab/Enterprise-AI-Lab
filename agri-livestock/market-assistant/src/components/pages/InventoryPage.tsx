import { useMemo } from 'react'
import { motion } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import { Warehouse, AlertTriangle, ShieldCheck, TrendingDown } from 'lucide-react'
import { getInventoryData, getCommodityData, type InventoryItem } from '@/data/mockData'
import { formatPrice } from '@/lib/utils'
import type { CommodityId } from '@/context/AppContext'

function InventoryCard({ item, delay }: { readonly item: InventoryItem; readonly delay: number }) {
  const statusCfg = {
    safe: { color: 'border-up/30', badge: 'bg-up/10 text-up', icon: ShieldCheck, label: '安全' },
    warning: { color: 'border-warning/30', badge: 'bg-warning/10 text-warning', icon: AlertTriangle, label: '预警' },
    danger: { color: 'border-down/30', badge: 'bg-down/10 text-down', icon: AlertTriangle, label: '紧急' },
  }
  const cfg = statusCfg[item.status]
  const Icon = cfg.icon
  const pct = Math.min(item.currentDays / (item.safetyDays * 2), 1)
  const barColor = item.status === 'danger' ? 'bg-down' : item.status === 'warning' ? 'bg-warning' : 'bg-up'

  // 库存联动采购推荐
  const cd = getCommodityData(item.commodityId as CommodityId)
  const gap = item.status !== 'safe' ? Math.round((item.safetyDays - item.currentDays) * item.dailyConsumption) : 0

  const trendOption = {
    backgroundColor: 'transparent',
    grid: { left: 0, right: 0, top: 4, bottom: 4 },
    xAxis: { type: 'category' as const, show: false, data: item.trend30d.map((_, i) => i) },
    yAxis: { type: 'value' as const, show: false },
    series: [{ type: 'line' as const, data: item.trend30d, smooth: true, symbol: 'none',
      lineStyle: { color: item.status === 'danger' ? '#ef4444' : item.status === 'warning' ? '#f59e0b' : '#22c55e', width: 1.5 },
      areaStyle: { color: { type: 'linear' as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [
        { offset: 0, color: item.status === 'danger' ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)' },
        { offset: 1, color: 'transparent' }
      ] } },
    }],
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.4 }}
      className={`card-base p-4 ${cfg.color} ${item.status === 'danger' ? 'alert-pulse' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        <span className="font-display text-sm font-bold text-text-primary">{item.commodityName}</span>
        <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${cfg.badge}`}>
          <Icon size={10} />{cfg.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-3 text-center">
        <div>
          <span className="text-[10px] text-text-muted block">当前库存</span>
          <span className="font-mono text-sm font-semibold text-text-primary">{formatPrice(item.currentStock)}吨</span>
        </div>
        <div>
          <span className="text-[10px] text-text-muted block">可用天数</span>
          <span className={`font-mono text-sm font-semibold ${item.status === 'danger' ? 'text-down' : item.status === 'warning' ? 'text-warning' : 'text-up'}`}>{item.currentDays}天</span>
        </div>
        <div>
          <span className="text-[10px] text-text-muted block">日均消耗</span>
          <span className="font-mono text-sm font-semibold text-text-secondary">{item.dailyConsumption}吨/天</span>
        </div>
      </div>

      {/* Days bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
          <span>安全线 {item.safetyDays}天</span>
          <span>{item.currentDays}/{item.safetyDays * 2}天</span>
        </div>
        <div className="h-1.5 rounded-full bg-bg-elevated overflow-hidden relative">
          <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct * 100}%` }} />
          <div className="absolute top-0 h-full w-px bg-text-muted" style={{ left: '50%' }} />
        </div>
      </div>

      {/* Trend */}
      <ReactECharts option={trendOption} style={{ height: 50 }} opts={{ renderer: 'canvas' }} />

      {/* Purchase recommendation */}
      {item.status !== 'safe' && (
        <div className={`mt-3 p-2 rounded text-xs ${item.status === 'danger' ? 'bg-down/10 border border-down/20' : 'bg-warning/10 border border-warning/20'}`}>
          <div className="flex items-center gap-1 mb-1">
            <TrendingDown size={10} className={item.status === 'danger' ? 'text-down' : 'text-warning'} />
            <span className={`font-medium ${item.status === 'danger' ? 'text-down' : 'text-warning'}`}>
              {item.status === 'danger' ? '紧急补货' : '建议补货'}
            </span>
          </div>
          <p className="text-text-muted">
            缺口 <span className="font-mono text-text-primary">{formatPrice(gap)}吨</span>，
            建议价 ≤<span className="font-mono text-recommend">{formatPrice(cd.procurementSummary.idealBuyBelow)}</span>元/吨
          </p>
        </div>
      )}
    </motion.div>
  )
}

export default function InventoryPage() {
  const inventory = useMemo(() => getInventoryData(), [])
  const dangerCount = inventory.filter(i => i.status === 'danger').length
  const warningCount = inventory.filter(i => i.status === 'warning').length

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Warehouse size={20} className="text-neon" />
            <h2 className="font-display text-lg font-bold text-text-primary">库存管理</h2>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {dangerCount > 0 && <span className="px-2 py-1 rounded bg-down/10 text-down">{dangerCount} 品种紧急</span>}
            {warningCount > 0 && <span className="px-2 py-1 rounded bg-warning/10 text-warning">{warningCount} 品种预警</span>}
            <span className="px-2 py-1 rounded bg-up/10 text-up">{inventory.length - dangerCount - warningCount} 品种安全</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {inventory
            .sort((a, b) => { const order = { danger: 0, warning: 1, safe: 2 }; return order[a.status] - order[b.status] })
            .map((item, i) => <InventoryCard key={item.commodityId} item={item} delay={i * 0.08} />)}
        </div>
      </motion.div>
    </div>
  )
}
