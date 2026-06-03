import { useCallback } from 'react'
import { motion } from 'framer-motion'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { allDates, todayIndex, type CommodityDataSet } from '@/data/mockData'
import { formatDate } from '@/lib/utils'

interface Props {
  readonly data: CommodityDataSet
  readonly commodityName: string
  readonly onDeviationClick?: (id: string) => void
}

export default function ThreeLineChart({ data, commodityName, onDeviationClick }: Props) {
  const dates = allDates.map(formatDate)
  const { forecastPrices, confidenceIntervals, procurementData, deviationEvents, actualPrices } = data

  const ci95Lower = confidenceIntervals.map(c => c.ci95[0])
  const ci95Upper = confidenceIntervals.map((c, i) => c.ci95[1] - ci95Lower[i])
  const ci80Lower = confidenceIntervals.map(c => c.ci80[0])
  const ci80Upper = confidenceIntervals.map((c, i) => c.ci80[1] - ci80Lower[i])

  const procLower = allDates.map(d => { const p = procurementData.find(pd => pd.date === d); return p ? p.acceptableLower : null })
  const procBand = allDates.map(d => { const p = procurementData.find(pd => pd.date === d); return p ? p.acceptableUpper - p.acceptableLower : null })

  const deviationMarkers = deviationEvents.map(ev => ({
    name: ev.id, coord: [formatDate(ev.date), ev.actual],
    symbol: ev.level === 'ALERT' ? 'diamond' : ev.level === 'WARNING' ? 'triangle' : 'circle',
    symbolSize: ev.level === 'ALERT' ? 16 : ev.level === 'WARNING' ? 14 : 10,
    itemStyle: { color: ev.level === 'ALERT' ? '#f43f5e' : ev.level === 'WARNING' ? '#f59e0b' : '#818cf8', borderColor: '#fff', borderWidth: 1 },
    label: { show: ev.deviationRate >= 0.03, position: 'top' as const, formatter: `${ev.deviationRate > 0 ? '+' : ''}${(ev.deviationRate * 100).toFixed(1)}%`, color: ev.level === 'WARNING' ? '#f59e0b' : '#f43f5e', fontSize: 10, fontFamily: 'IBM Plex Mono' },
  }))

  const procMarkers = procurementData.filter(p => p.volume !== null).slice(0, 5).map(p => ({
    name: p.action, coord: [formatDate(p.date), p.acceptableLower - 30],
    symbol: 'arrow', symbolSize: [10, 14], symbolRotate: 180,
    itemStyle: { color: '#10b981' },
    label: { show: true, position: 'bottom' as const, formatter: `${p.action}\n${p.volume}吨`, color: '#10b981', fontSize: 9, fontFamily: 'DM Sans', lineHeight: 13 },
  }))

  // Dynamic Y axis range
  const allValues = [...actualPrices.filter((v): v is number => v !== null), ...forecastPrices]
  const yMin = Math.floor(Math.min(...allValues) / 100) * 100 - 100
  const yMax = Math.ceil(Math.max(...allValues) / 100) * 100 + 100

  const option: EChartsOption = {
    backgroundColor: 'transparent', animation: true, animationDuration: 1200, animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis', backgroundColor: 'rgba(15,23,42,0.95)', borderColor: 'rgba(148,163,184,0.6)', borderWidth: 1,
      textStyle: { color: '#fff', fontFamily: 'DM Sans', fontSize: 12 },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const dateLabel = params[0]?.axisValue || ''
        let html = `<div style="font-family:Space Grotesk;font-weight:600;margin-bottom:6px">${dateLabel}</div>`
        for (const p of params) {
          if (['ci95_lower','ci95_band','ci80_lower','ci80_band','proc_lower','proc_band'].includes(p.seriesName)) continue
          if (p.value == null || p.value === '-') continue
          const color = p.color?.colorStops ? p.color.colorStops[0].color : p.color
          html += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0"><span style="width:8px;height:8px;border-radius:50%;background:${color};display:inline-block"></span><span style="color:#94a3b8">${p.seriesName}</span><span style="font-family:JetBrains Mono;font-weight:600;margin-left:auto">${typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</span></div>`
        }
        return html
      },
    },
    legend: { bottom: 0, left: 'center', textStyle: { color: '#94a3b8', fontFamily: 'DM Sans', fontSize: 12 }, itemWidth: 16, itemHeight: 3, itemGap: 24, data: [{ name: '实际线', icon: 'roundRect' }, { name: '预测线', icon: 'roundRect' }, { name: '采购推荐区间', icon: 'roundRect' }] },
    grid: { left: 60, right: 24, top: 24, bottom: 48, containLabel: false },
    xAxis: { type: 'category', data: dates, axisLine: { lineStyle: { color: 'rgba(148,163,184,0.6)' } }, axisTick: { show: false }, axisLabel: { color: '#475569', fontFamily: 'IBM Plex Mono', fontSize: 10, interval: 4 }, splitLine: { show: false } },
    yAxis: { type: 'value', min: yMin, max: yMax, axisLine: { show: false }, axisTick: { show: false }, axisLabel: { color: '#475569', fontFamily: 'IBM Plex Mono', fontSize: 10, formatter: (v: number) => v.toLocaleString() }, splitLine: { lineStyle: { color: 'rgba(148,163,184,0.25)', type: 'dashed' } } },
    series: [
      { name: 'ci95_lower', type: 'line', data: ci95Lower, lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, stack: 'ci95', symbol: 'none', silent: true, z: 1 },
      { name: 'ci95_band', type: 'line', data: ci95Upper, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(129,140,248,0.06)' }, stack: 'ci95', symbol: 'none', silent: true, z: 1 },
      { name: 'ci80_lower', type: 'line', data: ci80Lower, lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, stack: 'ci80', symbol: 'none', silent: true, z: 2 },
      { name: 'ci80_band', type: 'line', data: ci80Upper, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(129,140,248,0.10)' }, stack: 'ci80', symbol: 'none', silent: true, z: 2 },
      { name: 'proc_lower', type: 'line', data: procLower, lineStyle: { opacity: 0 }, areaStyle: { opacity: 0 }, stack: 'proc', symbol: 'none', silent: true, z: 3 },
      { name: 'proc_band', type: 'line', data: procBand, lineStyle: { opacity: 0 }, areaStyle: { color: 'rgba(16,185,129,0.12)' }, stack: 'proc', symbol: 'none', silent: true, z: 3 },
      { name: '预测线', type: 'line', data: forecastPrices, lineStyle: { color: '#818cf8', width: 2, type: 'dashed' }, itemStyle: { color: '#818cf8' }, symbol: 'circle', symbolSize: 0, showSymbol: false, z: 5, markPoint: { data: procMarkers, animation: true } },
      { name: '实际线', type: 'line', data: actualPrices.map(v => v ?? '-'), lineStyle: { color: '#14b8a6', width: 3 }, itemStyle: { color: '#14b8a6' }, symbol: 'circle', symbolSize: 0, showSymbol: false, z: 10,
        markPoint: { data: deviationMarkers, animation: true },
        markLine: { symbol: ['none', 'none'], lineStyle: { color: 'rgba(20,184,166,0.5)', type: 'solid', width: 1 }, label: { formatter: '当前', color: '#14b8a6', fontFamily: 'Plus Jakarta Sans', fontSize: 11, position: 'start' }, data: [{ xAxis: dates[todayIndex] }] },
      },
      { name: '采购推荐区间', type: 'line', data: [], lineStyle: { color: '#10b981', width: 0 }, itemStyle: { color: '#10b981' }, z: 0 },
    ],
  }

  const handleClick = useCallback((params: any) => {
    if (params.componentType === 'markPoint' && params.name?.startsWith('DEV-')) onDeviationClick?.(params.name)
  }, [onDeviationClick])

  return (
    <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }} className="card-base p-4">
      <div className="flex items-center justify-between mb-2 px-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">{commodityName} — 三线预测走势</span>
          <span className="text-xs text-text-muted font-mono">2026.03.16 — 2026.05.15</span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-actual rounded" /><span className="text-text-muted">实际</span></span>
          <span className="flex items-center gap-1.5"><span className="w-4 h-0.5 bg-forecast rounded border-t border-dashed border-forecast" /><span className="text-text-muted">预测</span></span>
          <span className="flex items-center gap-1.5"><span className="w-4 h-2 bg-recommend/20 rounded" /><span className="text-text-muted">采购区间</span></span>
        </div>
      </div>
      <ReactECharts option={option} style={{ height: 400 }} onEvents={{ click: handleClick }} opts={{ renderer: 'canvas' }} />
    </motion.div>
  )
}
