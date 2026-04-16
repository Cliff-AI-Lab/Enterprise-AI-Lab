import { motion } from 'framer-motion'
import { Database, Globe, CreditCard, Upload, Play, CheckCircle2, XCircle, Clock, ShieldCheck, AlertTriangle, BarChart3 } from 'lucide-react'
import CollapsibleSection from '@/components/shared/CollapsibleSection'

const publicSources = [
  { name: '大连商品交易所', type: 'AI抓取', url: 'dce.com.cn', status: 'ok', freq: '实时', lastSync: '刚刚', records: 2340 },
  { name: '中国气象局', type: 'AI抓取', url: 'weather.cma.cn', status: 'ok', freq: '每日', lastSync: '30分钟前', records: 890 },
  { name: '船讯网', type: 'AI抓取', url: 'shipinfo.net', status: 'ok', freq: '每日', lastSync: '5分钟前', records: 456 },
  { name: 'CBOT行情', type: 'AI抓取', url: 'cmegroup.com', status: 'ok', freq: '实时', lastSync: '刚刚', records: 1820 },
]
const paidSources = [
  { name: '卓创资讯', type: '付费API', url: 'api.sci99.com', status: 'error', freq: '每小时', lastSync: '15分钟前(超时)', records: 5600 },
  { name: '我的钢铁网', type: '付费API', url: 'api.mysteel.com', status: 'ok', freq: '每日', lastSync: '1小时前', records: 3200 },
]
const manualImports = [
  { name: '2026Q1采购价格汇总.xlsx', uploader: '李四', date: '2026-04-10', rows: 342, status: '已入库' },
  { name: '供应商报价对比表.csv', uploader: '张三', date: '2026-04-08', rows: 56, status: '已入库' },
  { name: '鱼粉港口库存-周报.xlsx', uploader: '王五', date: '2026-04-05', rows: 28, status: '已入库' },
]
const collectTasks = [
  { name: '豆粕期货日线数据', source: '大商所', cron: '每日 08:00', lastRun: '08:00 成功', next: '明日 08:00', rate: '100%' },
  { name: '现货报价采集', source: '卓创+钢铁网', cron: '每小时', lastRun: '09:00 失败', next: '10:00', rate: '85%' },
  { name: '天气预警监控', source: '气象局', cron: '每日 06:00', lastRun: '06:00 成功', next: '明日 06:00', rate: '98%' },
  { name: '海运费率更新', source: '船讯网', cron: '每日 07:00', lastRun: '07:00 成功', next: '明日 07:00', rate: '96%' },
]
const qualityMetrics = [
  { dimension: '数据准确率', score: 94.2, status: 'good', desc: '通过交叉验证的数据占比' },
  { dimension: '数据完整率', score: 89.5, status: 'good', desc: '非空字段占比' },
  { dimension: '数据时效性', score: 78.3, status: 'warn', desc: '在更新周期内的数据占比（卓创延迟影响）' },
]
const anomalies = [
  { time: '09:15', source: '卓创资讯', type: '接口超时', desc: '连续3次请求失败，已切换至备用缓存', level: 'error' },
  { time: '08:30', source: '大商所', type: '数据异常', desc: '豆粕期货价格跳变>5%，AI判定为盘中波动，已标记', level: 'warn' },
  { time: '07:00', source: '手工导入', type: '格式校验', desc: '上传文件缺少"日期"列，已拒绝入库', level: 'warn' },
]

const StatusDot = ({ ok }: { ok: boolean }) => ok ? <CheckCircle2 size={12} className="text-up" /> : <XCircle size={12} className="text-down" />

export default function DataManagePage() {
  return (
    <div className="flex-1 p-4 overflow-y-auto ">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="font-display text-xl font-bold text-text-primary mb-1">数据管理</h2>
        <p className="text-xs text-text-muted mb-6">基础数据对接 + AI数据清洗与识别</p>

        <CollapsibleSection title="数据源配置" icon={<Database size={14} />} badge={<span className="text-xs text-text-muted">6个数据源</span>} defaultOpen>
          <div className="mb-4">
            <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-2"><Globe size={12} />公开信息（AI自动抓取）</h4>
            <div className="space-y-1.5">
              {publicSources.map(s => (
                <div key={s.name} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated text-sm">
                  <StatusDot ok={s.status === 'ok'} />
                  <span className="text-text-primary w-36">{s.name}</span>
                  <span className="text-xs font-mono text-text-muted flex-1">{s.url}</span>
                  <span className="text-xs text-text-muted w-16">{s.freq}</span>
                  <span className="text-xs text-text-muted w-24">{s.lastSync}</span>
                  <span className="text-xs font-mono text-text-secondary">{s.records.toLocaleString()}条</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mb-4">
            <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-2"><CreditCard size={12} />付费接口</h4>
            <div className="space-y-1.5">
              {paidSources.map(s => (
                <div key={s.name} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated text-sm">
                  <StatusDot ok={s.status === 'ok'} />
                  <span className="text-text-primary w-36">{s.name}</span>
                  <span className="text-xs font-mono text-text-muted flex-1">{s.url}</span>
                  <span className="text-xs text-text-muted w-16">{s.freq}</span>
                  <span className="text-xs text-text-muted w-24">{s.lastSync}</span>
                  <span className="text-xs font-mono text-text-secondary">{s.records.toLocaleString()}条</span>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-2"><Upload size={12} />人工导入记录</h4>
            <div className="space-y-1.5">
              {manualImports.map(m => (
                <div key={m.name} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated text-sm">
                  <Upload size={12} className="text-text-muted" />
                  <span className="text-text-primary flex-1 truncate">{m.name}</span>
                  <span className="text-xs text-text-muted">{m.uploader}</span>
                  <span className="text-xs font-mono text-text-muted">{m.date}</span>
                  <span className="text-xs font-mono text-text-secondary">{m.rows}行</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up">{m.status}</span>
                </div>
              ))}
            </div>
            <button className="mt-3 px-3 py-1.5 rounded border border-dashed border-border-default text-xs text-text-muted hover:text-neon hover:border-neon/50 transition-colors flex items-center gap-1">
              <Upload size={12} />上传文件 (Excel/CSV)
            </button>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="数据采集任务" icon={<Play size={14} />} badge={<span className="text-xs text-text-muted">{collectTasks.length}个任务</span>}>
          <div className="space-y-1.5">
            {collectTasks.map(t => (
              <div key={t.name} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated text-sm">
                <Clock size={12} className="text-text-muted" />
                <span className="text-text-primary w-40">{t.name}</span>
                <span className="text-xs text-text-muted w-28">{t.source}</span>
                <span className="text-xs font-mono text-text-muted w-24">{t.cron}</span>
                <span className={`text-xs w-24 ${t.lastRun.includes('失败') ? 'text-down' : 'text-text-muted'}`}>{t.lastRun}</span>
                <span className="text-xs text-text-muted w-24">{t.next}</span>
                <span className={`text-xs font-mono ${parseFloat(t.rate) > 90 ? 'text-up' : 'text-warning'}`}>{t.rate}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="数据清洗 & 质量报告" icon={<ShieldCheck size={14} />} badge={<span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up">质量良好</span>}>
          <div className="grid grid-cols-3 gap-3 mb-4">
            {qualityMetrics.map(m => (
              <div key={m.dimension} className="p-3 rounded bg-bg-elevated">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-text-primary">{m.dimension}</span>
                  <span className={`font-display text-xl font-bold ${m.status === 'good' ? 'text-up' : 'text-warning'}`}>{m.score}%</span>
                </div>
                <p className="text-[10px] text-text-muted">{m.desc}</p>
              </div>
            ))}
          </div>
          <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-2"><AlertTriangle size={12} />异常记录（今日）</h4>
          <div className="space-y-1.5">
            {anomalies.map((a, i) => (
              <div key={i} className="flex items-start gap-3 p-2.5 rounded bg-bg-elevated text-xs">
                <span className="font-mono text-text-muted w-10 shrink-0">{a.time}</span>
                {a.level === 'error' ? <XCircle size={12} className="text-down mt-0.5" /> : <AlertTriangle size={12} className="text-warning mt-0.5" />}
                <span className="text-text-secondary w-20">{a.source}</span>
                <span className="text-text-muted flex-1">{a.desc}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      </motion.div>
    </div>
  )
}
