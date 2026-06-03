import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Bot, Database, Brain, Power, CheckCircle2, XCircle, AlertTriangle, Activity, Clock } from 'lucide-react'
import CollapsibleSection from '@/components/shared/CollapsibleSection'
import { getAgentList, type AgentInfo } from '@/data/mockData'
import { formatPercent } from '@/lib/utils'

export default function AgentManagePage() {
  const initial = useMemo(() => getAgentList(), [])
  const [agents, setAgents] = useState(initial)

  const toggleAgent = (id: string) => {
    setAgents(prev => prev.map(a => a.id === id ? { ...a, enabled: !a.enabled, status: (!a.enabled ? (a.id === 'agent-collect' ? 'error' : 'running') : 'paused') as AgentInfo['status'] } : a))
  }

  const running = agents.filter(a => a.status === 'running').length
  const errors = agents.filter(a => a.status === 'error').length
  const allLogs = agents.flatMap(a => a.logs.map(l => ({ ...l, agent: a.name }))).sort((a, b) => b.time.localeCompare(a.time))
  const logIcons = { info: Activity, warn: AlertTriangle, error: XCircle }
  const logColors = { info: 'text-text-muted', warn: 'text-warning', error: 'text-down' }

  return (
    <div className="flex-1 p-4 overflow-y-auto ">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="font-display text-xl font-bold text-text-primary mb-1">智能体管理</h2>
            <p className="text-xs text-text-muted">配置、监控、启停智能体</p>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="px-2 py-1 rounded bg-up/10 text-up flex items-center gap-1"><Power size={10} />{running} 运行</span>
            {errors > 0 && <span className="px-2 py-1 rounded bg-down/10 text-down flex items-center gap-1"><XCircle size={10} />{errors} 异常</span>}
          </div>
        </div>

        <CollapsibleSection title="智能体列表" icon={<Bot size={14} />} badge={<span className="text-xs text-text-muted">{agents.length}个</span>} defaultOpen>
          <div className="space-y-3">
            {agents.map(agent => {
              const sCfg = { running: { color: 'text-up', icon: CheckCircle2, label: '运行中' }, paused: { color: 'text-text-muted', icon: Clock, label: '已暂停' }, error: { color: 'text-down', icon: XCircle, label: '异常' } }
              const s = sCfg[agent.status]
              const SIcon = s.icon
              return (
                <div key={agent.id} className={`p-4 rounded border ${agent.status === 'error' ? 'border-down/30' : 'border-border-default'} bg-bg-elevated`}>
                  <div className="flex items-center gap-3 mb-3">
                    <Bot size={18} className={agent.enabled ? 'text-neon' : 'text-text-muted'} />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-display font-bold text-text-primary">{agent.name}</span>
                        <span className={`text-xs flex items-center gap-1 ${s.color}`}><SIcon size={10} />{s.label}</span>
                      </div>
                      <p className="text-xs text-text-muted mt-0.5">{agent.description}</p>
                    </div>
                    <button onClick={() => toggleAgent(agent.id)} className={`relative w-11 h-6 rounded-full transition-colors ${agent.enabled ? 'bg-neon' : 'bg-bg-primary border border-border-default'}`}>
                      <motion.div animate={{ x: agent.enabled ? 22 : 3 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }} className={`absolute top-1 w-4 h-4 rounded-full ${agent.enabled ? 'bg-text-inverse' : 'bg-text-muted'}`} />
                    </button>
                  </div>
                  <div className="flex items-center gap-6 text-xs">
                    <span className="flex items-center gap-1.5"><Database size={10} className="text-forecast" />数据源: {agent.id === 'agent-collect' ? '商情/大商所/卓创/船讯' : agent.id === 'agent-forecast' ? '全部数据' : agent.id === 'agent-deviation' ? '预测+实际数据' : '预测+库存+需求'}</span>
                    <span className="flex items-center gap-1.5"><Brain size={10} className="text-neon" />模型: {agent.id === 'agent-forecast' ? 'SARIMA+随机森林+融合' : agent.id === 'agent-deviation' ? 'DeepSeek V3.1' : agent.id === 'agent-procure' ? '融合模型+优化器' : '—'}</span>
                    <span className="text-text-muted ml-auto">成功率 <span className={`font-mono font-semibold ${agent.successRate > 0.9 ? 'text-up' : 'text-warning'}`}>{formatPercent(agent.successRate)}</span></span>
                    <span className="text-text-muted">24h <span className="font-mono text-text-primary">{agent.runCount24h}次</span></span>
                  </div>
                </div>
              )
            })}
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="运行监控" icon={<Activity size={14} />} badge={errors > 0 ? <span className="text-xs px-1.5 py-0.5 rounded bg-down/10 text-down">{errors}项异常</span> : <span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up">正常</span>}>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1"><Database size={11} />数据状态</h4>
              <div className="space-y-1.5">
                {['商情平台', '大商所', '船讯网', '气象局'].map(s => (
                  <div key={s} className="flex items-center gap-2 p-2 rounded bg-bg-primary text-xs"><CheckCircle2 size={10} className="text-up" /><span className="text-text-secondary">{s}</span><span className="text-text-muted ml-auto">正常</span></div>
                ))}
                <div className="flex items-center gap-2 p-2 rounded bg-bg-primary text-xs"><XCircle size={10} className="text-down" /><span className="text-text-secondary">卓创资讯</span><span className="text-down ml-auto">超时</span></div>
              </div>
            </div>
            <div>
              <h4 className="text-xs text-text-muted uppercase tracking-widest mb-2 flex items-center gap-1"><Brain size={11} />模型状态</h4>
              <div className="space-y-1.5">
                {['SARIMA', '随机森林', 'XGBoost', '融合模型'].map(m => (
                  <div key={m} className="flex items-center gap-2 p-2 rounded bg-bg-primary text-xs"><CheckCircle2 size={10} className="text-up" /><span className="text-text-secondary">{m}</span><span className="text-text-muted ml-auto">在线</span></div>
                ))}
                <div className="flex items-center gap-2 p-2 rounded bg-bg-primary text-xs"><Clock size={10} className="text-text-muted" /><span className="text-text-secondary">LSTM</span><span className="text-text-muted ml-auto">待命</span></div>
              </div>
            </div>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="运行日志 & 告警" icon={<AlertTriangle size={14} />} badge={<span className="text-xs text-text-muted">今日 {allLogs.length} 条</span>}>
          <div className="space-y-1.5 max-h-[300px] overflow-y-auto">
            {allLogs.map((log, i) => {
              const LIcon = logIcons[log.level]
              return (
                <div key={i} className="flex items-start gap-3 p-2 rounded bg-bg-elevated text-xs">
                  <span className="font-mono text-text-muted w-10 shrink-0">{log.time}</span>
                  <LIcon size={11} className={`${logColors[log.level]} mt-0.5 shrink-0`} />
                  <span className="text-text-muted w-28 shrink-0">{log.agent}</span>
                  <span className="text-text-secondary">{log.message}</span>
                </div>
              )
            })}
          </div>
        </CollapsibleSection>
      </motion.div>
    </div>
  )
}
