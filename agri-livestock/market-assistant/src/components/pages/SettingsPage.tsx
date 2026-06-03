import { useState } from 'react'
import { motion } from 'framer-motion'
import { Settings, Database, Link2, Brain, Bell, CheckCircle2, XCircle, ExternalLink, Plus, Trash2 } from 'lucide-react'

interface DataSource { name: string; url: string; status: 'connected' | 'error' | 'disabled'; lastSync: string }
interface CustomLink { id: string; name: string; url: string }

const defaultSources: DataSource[] = [
  { name: '商情平台', url: 'https://sq.internal.corp/api', status: 'connected', lastSync: '2分钟前' },
  { name: '大商所行情', url: 'https://www.dce.com.cn/api', status: 'connected', lastSync: '实时' },
  { name: '卓创资讯', url: 'https://api.sci99.com/v2', status: 'error', lastSync: '15分钟前(超时)' },
  { name: '船讯网物流', url: 'https://api.shipinfo.net/v1', status: 'connected', lastSync: '5分钟前' },
  { name: '气象数据', url: 'https://weather.cma.cn/api', status: 'connected', lastSync: '30分钟前' },
]

const defaultLinks: CustomLink[] = [
  { id: '1', name: '企业ERP系统', url: 'https://erp.internal.corp' },
  { id: '2', name: '供应商管理平台', url: 'https://scm.internal.corp' },
  { id: '3', name: '大商所官网', url: 'https://www.dce.com.cn' },
]

const models = [
  { id: 'deepseek-v3.1', name: 'DeepSeek V3.1', desc: '快速响应，适合日常分析' },
  { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', desc: '高质量推理' },
  { id: 'qwen3.5-397b', name: 'Qwen 3.5 397B', desc: '大参数模型，深度分析' },
  { id: 'ruidong-pro', name: '睿动Pro', desc: '平台推荐模型' },
]

export default function SettingsPage() {
  const [sources] = useState(defaultSources)
  const [links, setLinks] = useState(defaultLinks)
  const [selectedModel, setSelectedModel] = useState('deepseek-v3.1')
  const [temperature, setTemperature] = useState(0.7)
  const [thresholds, setThresholds] = useState({ notice: 2, warning: 5, alert: 10, safetyDays: 7 })

  const removeLink = (id: string) => setLinks(prev => prev.filter(l => l.id !== id))
  const addLink = () => setLinks(prev => [...prev, { id: Date.now().toString(), name: '新链接', url: 'https://' }])

  const statusIcon = { connected: <CheckCircle2 size={12} className="text-up" />, error: <XCircle size={12} className="text-down" />, disabled: <XCircle size={12} className="text-text-muted" /> }

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }} className="max-w-4xl">
        <div className="flex items-center gap-2 mb-6">
          <Settings size={20} className="text-neon" />
          <h2 className="font-display text-lg font-bold text-text-primary">系统配置</h2>
        </div>

        {/* Data Sources */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Database size={16} className="text-forecast" />
            <h3 className="text-sm font-display font-bold text-text-primary">数据源配置</h3>
          </div>
          <div className="space-y-2">
            {sources.map(s => (
              <div key={s.name} className="card-base p-3 flex items-center gap-3">
                {statusIcon[s.status]}
                <span className="text-sm text-text-primary w-24">{s.name}</span>
                <span className="text-xs font-mono text-text-muted flex-1 truncate">{s.url}</span>
                <span className="text-xs text-text-muted">{s.lastSync}</span>
                <button className="px-2 py-1 rounded text-xs bg-bg-elevated text-text-secondary hover:text-text-primary border border-border-default">测试连接</button>
              </div>
            ))}
          </div>
        </section>

        {/* External Links */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Link2 size={16} className="text-recommend" />
              <h3 className="text-sm font-display font-bold text-text-primary">外部链接管理</h3>
            </div>
            <button onClick={addLink} className="flex items-center gap-1 px-2 py-1 rounded text-xs bg-neon/10 text-neon hover:bg-neon/20"><Plus size={12} />添加</button>
          </div>
          <div className="space-y-2">
            {links.map(l => (
              <div key={l.id} className="card-base p-3 flex items-center gap-3">
                <ExternalLink size={12} className="text-text-muted" />
                <input defaultValue={l.name} className="bg-transparent text-sm text-text-primary outline-none w-32 border-b border-transparent focus:border-neon/50" />
                <input defaultValue={l.url} className="bg-transparent text-xs font-mono text-text-secondary outline-none flex-1 border-b border-transparent focus:border-neon/50" />
                <button onClick={() => removeLink(l.id)} className="p-1 rounded hover:bg-down/10 text-text-muted hover:text-down"><Trash2 size={12} /></button>
              </div>
            ))}
          </div>
        </section>

        {/* Model Config */}
        <section className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={16} className="text-neon" />
            <h3 className="text-sm font-display font-bold text-text-primary">AI模型配置</h3>
            <span className="text-[10px] text-text-muted font-mono ml-auto">睿动统一平台</span>
          </div>
          <div className="grid grid-cols-2 gap-2 mb-4">
            {models.map(m => (
              <button key={m.id} onClick={() => setSelectedModel(m.id)}
                className={`card-base p-3 text-left transition-all ${selectedModel === m.id ? 'border-neon/50 bg-neon/5' : ''}`}>
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${selectedModel === m.id ? 'bg-neon' : 'bg-text-muted'}`} />
                  <span className="text-sm font-medium text-text-primary">{m.name}</span>
                </div>
                <p className="text-xs text-text-muted mt-1 ml-4">{m.desc}</p>
              </button>
            ))}
          </div>
          <div className="card-base p-3 flex items-center gap-4">
            <span className="text-sm text-text-secondary">Temperature</span>
            <input type="range" min="0" max="1" step="0.1" value={temperature} onChange={e => setTemperature(+e.target.value)}
              className="flex-1 accent-neon" />
            <span className="font-mono text-sm text-neon w-8 text-right">{temperature}</span>
          </div>
        </section>

        {/* Alert Thresholds */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Bell size={16} className="text-warning" />
            <h3 className="text-sm font-display font-bold text-text-primary">预警阈值配置</h3>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              { key: 'notice' as const, label: '关注阈值', desc: '偏差达到此值记录', unit: '%', color: 'text-info' },
              { key: 'warning' as const, label: '预警阈值', desc: '触发AI自动分析', unit: '%', color: 'text-warning' },
              { key: 'alert' as const, label: '告警阈值', desc: '推送人工审核', unit: '%', color: 'text-down' },
              { key: 'safetyDays' as const, label: '安全库存天数', desc: '低于此值触发补货', unit: '天', color: 'text-recommend' },
            ].map(t => (
              <div key={t.key} className="card-base p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-sm font-medium ${t.color}`}>{t.label}</span>
                  <div className="flex items-center gap-1">
                    <input type="number" value={thresholds[t.key]}
                      onChange={e => setThresholds(prev => ({ ...prev, [t.key]: +e.target.value }))}
                      className="w-14 bg-bg-elevated border border-border-default rounded px-2 py-1 text-sm font-mono text-text-primary text-right outline-none focus:border-neon/50" />
                    <span className="text-xs text-text-muted">{t.unit}</span>
                  </div>
                </div>
                <p className="text-xs text-text-muted">{t.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </motion.div>
    </div>
  )
}
