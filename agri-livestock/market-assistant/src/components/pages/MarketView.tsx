import { useState } from 'react'
import { useApp } from '@/context/AppContext'
import { getCommodityData } from '@/data/mockData'
import MetricCard from '@/components/cards/MetricCard'
import ModelHealthCard from '@/components/cards/ModelHealthCard'
import DriverCard from '@/components/cards/DriverCard'
import ThreeLineChart from '@/components/charts/ThreeLineChart'
import DeviationList from '@/components/deviation/DeviationList'
import DeviationDetail from '@/components/deviation/DeviationDetail'
import ManualSupplement from '@/components/deviation/ManualSupplement'
import ProcurementPanel from '@/components/procurement/ProcurementPanel'
import AiChatPanel from '@/components/ai/AiChatPanel'
import RatingStars from '@/components/cards/RatingStars'
import { formatPercent } from '@/lib/utils'

export default function MarketView() {
  const { commodity, getCommodityDef } = useApp()
  const data = getCommodityData(commodity)
  const cc = data.coreConclusion
  const def = getCommodityDef()

  const [selectedDeviation, setSelectedDeviation] = useState<string | null>(null)
  const [supplementTarget, setSupplementTarget] = useState<string | null>(null)

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      {/* Top metrics */}
      <div className="grid grid-cols-4 gap-4 mb-5">
        <MetricCard label="当前价格" value={cc.currentPrice} unit={def.unit} change={0.023} subLabel="预测区间" subValue={`${cc.priceRange.lower}-${cc.priceRange.upper}`} accentColor="neon" delay={0.05} />
        <MetricCard label="明日预测价" value={cc.predictedPrice} unit={def.unit} change={cc.predictedChange} subLabel="置信度" subValue={formatPercent(cc.priceRange.confidence)} accentColor="forecast" delay={0.1} />
        <div className="card-base p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="w-2 h-2 rounded-full bg-up" />
            <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">趋势评估</span>
          </div>
          <div className="flex items-end gap-2">
            <span className="font-display text-3xl font-bold text-up tracking-tight">{Math.round(cc.trendAssessment.value * 100)}%</span>
            <span className="text-sm text-text-muted mb-1">看涨概率</span>
          </div>
          <div className={`flex items-center gap-1 mt-2 text-sm font-medium ${cc.trendAssessment.change >= 0 ? 'text-up' : 'text-down'}`}>
            {cc.trendAssessment.change >= 0 ? '+' : ''}{formatPercent(cc.trendAssessment.change)} 较上周
          </div>
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-border-default">
            <span className="text-xs text-text-muted">操作评级</span>
            <RatingStars rating={cc.actionRating} />
          </div>
        </div>
        <ModelHealthCard data={data.modelHealth} />
      </div>

      {/* Chart */}
      <div className="mb-5">
        <ThreeLineChart data={data} commodityName={def.name} onDeviationClick={setSelectedDeviation} />
      </div>

      {/* Bottom panels */}
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-3 min-w-0">
          <DeviationList events={data.deviationEvents} onSelect={setSelectedDeviation} selectedId={selectedDeviation} />
        </div>
        <div className="col-span-3 min-w-0">
          {selectedDeviation
            ? <DeviationDetail events={data.deviationEvents} deviationId={selectedDeviation} onClose={() => setSelectedDeviation(null)} onOpenSupplement={setSupplementTarget} />
            : <DriverCard factors={data.driverFactors} />}
        </div>
        <div className="col-span-6 min-w-0 space-y-4">
          <ProcurementPanel data={data.procurementSummary} unit={def.unit} />
          <AiChatPanel commodityName={def.name} commodityData={data} />
        </div>
      </div>

      <ManualSupplement deviationId={supplementTarget} onClose={() => setSupplementTarget(null)} />
    </div>
  )
}
