import { useState, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Bot, Power, CheckCircle2, AlertTriangle, XCircle, Clock, Activity } from 'lucide-react'
import { getAgentList, type AgentInfo } from '@/data/mockData'
import { formatPercent } from '@/lib/utils'

function AgentCard({ agent, onToggle, delay }: { readonly agent: AgentInfo; readonly onToggle: () => void; readonly delay: number }) {
  const statusCfg = {
    running: { color: 'text-up', bg: 'bg-up', icon: CheckCircle2, label: '运行中' },
    paused: { color: 'text-text-muted', bg: 'bg-text-muted', icon: Clock, label: '已暂停' },
    error: { color: 'text-down', bg: 'bg-down', icon: XCircle, label: '异常' },
  }
  const cfg = statusCfg[agent.status]
  const StatusIcon = cfg.icon

  const logLevelColor = { info: 'text-text-muted', warn: 'text-warning', error: 'text-down' }
  const logLevelIcon = { info: Activity, warn: AlertTriangle, error: XCircle }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay, duration: 0.4 }}
      className={`card-base p-5 ${agent.status === 'error' ? 'border-down/30' : ''}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${agent.enabled ? 'bg-neon/10' : 'bg-bg-elevated'}`}>
            <Bot size={20} className={agent.enabled ? 'text-neon' : 'text-text-muted'} />
          </div>
          <div>
            <h3 className="text-sm font-display font-bold text-text-primary">{agent.name}</h3>
            <div className="flex items-center gap-2 mt-0.5">
              <StatusIcon size={12} className={cfg.color} />
              <span className={`text-xs ${cfg.color}`}>{cfg.label}</span>
              <span className="text-[10px] text-text-muted font-mono">ID: {agent.id}</span>
            </div>
          </div>
        </div>

        {/* Toggle */}
        <button onClick={onToggle}
          className={`relative w-10 h-5 rounded-full transition-colors ${agent.enabled ? 'bg-neon' : 'bg-bg-elevated border border-border-default'}`}>
          <motion.div animate={{ x: agent.enabled ? 20 : 2 }} transition={{ type: 'spring', stiffness: 500, damping: 30 }}
            className={`absolute top-0.5 w-4 h-4 rounded-full ${agent.enabled ? 'bg-text-inverse' : 'bg-text-muted'}`} />
        </button>
      </div>

      <p className="text-xs text-text-muted mb-4 leading-relaxed">{agent.description}</p>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="p-2 rounded bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">成功率</span>
          <span className={`font-mono text-sm font-semibold ${agent.successRate > 0.9 ? 'text-up' : 'text-warning'}`}>{formatPercent(agent.successRate)}</span>
        </div>
        <div className="p-2 rounded bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">24h执行</span>
          <span className="font-mono text-sm font-semibold text-text-primary">{agent.runCount24h}次</span>
        </div>
        <div className="p-2 rounded bg-bg-elevated text-center">
          <span className="text-[10px] text-text-muted block mb-0.5">最近运行</span>
          <span className="font-mono text-[11px] font-semibold text-text-secondary">{agent.lastRun.split(' ')[1]}</span>
        </div>
      </div>

      {/* Logs */}
      <div>
        <span className="text-[10px] text-text-muted uppercase tracking-widest mb-2 block">最近日志</span>
        <div className="space-y-1.5 max-h-[120px] overflow-y-auto">
          {agent.logs.map((log, i) => {
            const LogIcon = logLevelIcon[log.level]
            return (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className="font-mono text-text-muted shrink-0 w-10">{log.time}</span>
                <LogIcon size={11} className={`${logLevelColor[log.level]} shrink-0 mt-0.5`} />
                <span className="text-text-secondary leading-relaxed">{log.message}</span>
              </div>
            )
          })}
        </div>
      </div>
    </motion.div>
  )
}

export default function AgentMonitor() {
  const initial = useMemo(() => getAgentList(), [])
  const [agents, setAgents] = useState(initial)

  const toggleAgent = (id: string) => {
    setAgents(prev => prev.map(a => a.id === id ? {
      ...a,
      enabled: !a.enabled,
      status: !a.enabled ? 'running' : 'paused' as AgentInfo['status'],
    } : a))
  }

  const running = agents.filter(a => a.status === 'running').length
  const errors = agents.filter(a => a.status === 'error').length

  return (
    <div className="flex-1 p-5 overflow-y-auto">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <Bot size={20} className="text-neon" />
            <h2 className="font-display text-lg font-bold text-text-primary">智能体监控</h2>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 px-2 py-1 rounded bg-up/10 text-up"><Power size={10} />{running} 运行中</span>
            {errors > 0 && <span className="flex items-center gap-1 px-2 py-1 rounded bg-down/10 text-down"><XCircle size={10} />{errors} 异常</span>}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {agents.map((agent, i) => (
            <AgentCard key={agent.id} agent={agent} onToggle={() => toggleAgent(agent.id)} delay={i * 0.1} />
          ))}
        </div>
      </motion.div>
    </div>
  )
}
