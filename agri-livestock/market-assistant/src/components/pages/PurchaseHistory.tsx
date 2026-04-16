import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { ShoppingBag, Search, Filter, TrendingDown, TrendingUp, Package } from 'lucide-react'
import { getPurchaseHistory } from '@/data/mockData'
import { COMMODITIES } from '@/context/AppContext'
import { formatPrice } from '@/lib/utils'

export default function PurchaseHistory() {
  const allRecords = useMemo(() => getPurchaseHistory(), [])
  const [filterCommodity, setFilterCommodity] = useState('全部')
  const [searchText, setSearchText] = useState('')

  const filtered = useMemo(() => {
    return allRecords.filter(r => {
      if (filterCommodity !== '全部' && r.commodity !== filterCommodity) return false
      if (searchText && !r.id.includes(searchText) && !r.supplier.includes(searchText)) return false
      return true
    })
  }, [allRecords, filterCommodity, searchText])

  const stats = useMemo(() => {
    const thisMonth = filtered.filter(r => r.date >= '2026-04-01')
    const totalQty = thisMonth.reduce((s, r) => s + r.quantity, 0)
    const totalAmt = thisMonth.reduce((s, r) => s + r.totalAmount, 0)
    const avgPrice = totalQty > 0 ? totalAmt / totalQty : 0
    return { count: thisMonth.length, totalQty, totalAmt, avgPrice }
  }, [filtered])

  const statusColors = { '已完成': 'bg-up/10 text-up', '运输中': 'bg-warning/10 text-warning', '待确认': 'bg-info/10 text-info' }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <ShoppingBag size={20} className="text-neon" />
            <h2 className="font-display text-lg font-bold text-text-primary">采购记录</h2>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-5">
          {[
            { label: '本月订单', value: `${stats.count}笔`, icon: Package, color: 'text-info' },
            { label: '采购总量', value: `${formatPrice(stats.totalQty)}吨`, icon: TrendingUp, color: 'text-neon' },
            { label: '采购总额', value: `${formatPrice(Math.round(stats.totalAmt / 10000))}万元`, icon: TrendingDown, color: 'text-warning' },
            { label: '加权均价', value: `${formatPrice(Math.round(stats.avgPrice))}元/吨`, icon: TrendingUp, color: 'text-up' },
          ].map((s) => (
            <div key={s.label} className="card-base p-4">
              <div className="flex items-center gap-2 mb-2">
                <s.icon size={14} className={s.color} />
                <span className="text-xs text-text-muted uppercase tracking-widest">{s.label}</span>
              </div>
              <span className="font-display text-xl font-bold text-text-primary">{s.value}</span>
            </div>
          ))}
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3 mb-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded border border-border-default bg-bg-card">
            <Search size={14} className="text-text-muted" />
            <input value={searchText} onChange={e => setSearchText(e.target.value)} placeholder="搜索订单号/供应商" className="bg-transparent text-sm text-text-primary placeholder:text-text-muted outline-none w-40" />
          </div>
          <div className="flex items-center gap-1">
            <Filter size={14} className="text-text-muted" />
            {['全部', ...COMMODITIES.map(c => c.name)].map(c => (
              <button key={c} onClick={() => setFilterCommodity(c)} className={`px-2.5 py-1 rounded text-xs transition-colors ${filterCommodity === c ? 'bg-neon text-text-inverse font-medium' : 'text-text-secondary hover:text-text-primary'}`}>{c}</button>
            ))}
          </div>
          <span className="ml-auto text-xs text-text-muted">{filtered.length} 条记录</span>
        </div>

        {/* Table */}
        <div className="card-base overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-default">
                {['订单号', '日期', '品种', '采购量', '成交均价', '金额', '供应商', '状态'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-widest">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 20).map((r) => (
                <tr key={r.id} className="border-b border-border-default/50 hover:bg-bg-hover transition-colors">
                  <td className="px-4 py-2.5 font-mono text-xs text-text-secondary">{r.id}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-text-secondary">{r.date}</td>
                  <td className="px-4 py-2.5 text-text-primary">{r.commodity}</td>
                  <td className="px-4 py-2.5 font-mono text-text-primary text-right">{r.quantity.toLocaleString()}</td>
                  <td className="px-4 py-2.5 font-mono text-text-primary text-right">{r.unitPrice.toLocaleString()}</td>
                  <td className="px-4 py-2.5 font-mono text-neon text-right">{formatPrice(Math.round(r.totalAmount / 10000))}万</td>
                  <td className="px-4 py-2.5 text-text-secondary">{r.supplier}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded ${statusColors[r.status]}`}>{r.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  )
}
