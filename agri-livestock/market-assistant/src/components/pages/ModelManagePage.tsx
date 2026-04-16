import { motion } from 'framer-motion'
import { Brain, Cloud, Cpu, CheckCircle2, Clock, BarChart3 } from 'lucide-react'
import CollapsibleSection from '@/components/shared/CollapsibleSection'
import { formatPercent } from '@/lib/utils'

const llmModels = [
  { id: 'deepseek-v3.1', name: 'DeepSeek V3.1', provider: '睿动平台', status: 'active', calls24h: 342, avgLatency: '1.2s', desc: '当前默认模型，日常分析推理' },
  { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', provider: '睿动平台', status: 'available', calls24h: 28, avgLatency: '2.8s', desc: '复杂归因分析场景' },
  { id: 'qwen3.5-397b', name: 'Qwen 3.5 397B', provider: '睿动平台', status: 'available', calls24h: 15, avgLatency: '3.5s', desc: '深度研究报告生成' },
  { id: 'ruidong-pro', name: '睿动Pro', provider: '睿动平台', status: 'available', calls24h: 8, avgLatency: '0.8s', desc: '轻量快速响应' },
]

const predictionModels = [
  { id: 'sarima', name: 'SARIMA', type: '时序模型', version: 'v2.3', status: 'running', accuracy: 0.89, lastTrain: '2026-04-14', calls7d: 168, desc: '季节性趋势捕捉，基础预测' },
  { id: 'rf', name: '随机森林', type: '集成模型', version: 'v2.1', status: 'running', accuracy: 0.91, lastTrain: '2026-04-14', calls7d: 168, desc: '多因子非线性建模，残差修正' },
  { id: 'lstm', name: 'LSTM', type: '深度学习', version: 'v1.5', status: 'standby', accuracy: 0.87, lastTrain: '2026-04-10', calls7d: 35, desc: '高波动场景备选，捕捉非线性动态' },
  { id: 'xgboost', name: 'XGBoost', type: '集成模型', version: 'v1.8', status: 'running', accuracy: 0.90, lastTrain: '2026-04-13', calls7d: 84, desc: '因子权重排序，特征重要性分析' },
  { id: 'ensemble', name: '融合模型', type: '集成', version: 'v3.0', status: 'running', accuracy: 0.93, lastTrain: '2026-04-14', calls7d: 168, desc: 'SARIMA+随机森林加权融合，最终输出' },
]

const statusCfg = { running: { label: '运行中', color: 'text-up', bg: 'bg-up/10' }, standby: { label: '待命', color: 'text-text-muted', bg: 'bg-bg-elevated' }, active: { label: '使用中', color: 'text-neon', bg: 'bg-neon/10' }, available: { label: '可用', color: 'text-text-muted', bg: 'bg-bg-elevated' } }

export default function ModelManagePage() {
  return (
    <div className="flex-1 p-4 overflow-y-auto ">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="font-display text-xl font-bold text-text-primary mb-1">模型管理</h2>
        <p className="text-xs text-text-muted mb-6">大模型接入 + 预测模型库</p>

        <CollapsibleSection title="大模型接入（睿动统一平台）" icon={<Cloud size={14} />} badge={<span className="text-xs font-mono text-text-muted">iruidong.com/v1</span>} defaultOpen>
          <div className="p-3 rounded bg-bg-elevated mb-4 flex items-center gap-4">
            <div className="flex items-center gap-2"><CheckCircle2 size={14} className="text-up" /><span className="text-sm text-text-primary">平台连接正常</span></div>
            <span className="text-xs text-text-muted">API Base: https://iruidong.com/v1</span>
            <span className="text-xs text-text-muted ml-auto">今日调用: <span className="font-mono text-text-primary">393次</span></span>
          </div>
          <div className="space-y-2">
            {llmModels.map(m => {
              const cfg = statusCfg[m.status as keyof typeof statusCfg]
              return (
                <div key={m.id} className={`p-3 rounded border ${m.status === 'active' ? 'border-neon/30 bg-neon/5' : 'border-border-default bg-bg-elevated'} flex items-center gap-4`}>
                  <Brain size={16} className={m.status === 'active' ? 'text-neon' : 'text-text-muted'} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-text-primary">{m.name}</span>
                      <span className={`text-xs px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
                    </div>
                    <p className="text-xs text-text-muted mt-0.5">{m.desc}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs font-mono text-text-secondary">{m.calls24h}次/24h</div>
                    <div className="text-[10px] text-text-muted">延迟 {m.avgLatency}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="预测模型库（内置）" icon={<Cpu size={14} />} badge={<span className="text-xs text-text-muted">{predictionModels.length}个模型</span>} defaultOpen>
          <div className="space-y-3">
            {predictionModels.map(m => {
              const cfg = statusCfg[m.status as keyof typeof statusCfg]
              return (
                <div key={m.id} className="p-4 rounded border border-border-default bg-bg-elevated">
                  <div className="flex items-center gap-3 mb-3">
                    <Cpu size={16} className={m.status === 'running' ? 'text-up' : 'text-text-muted'} />
                    <span className="text-sm font-display font-bold text-text-primary">{m.name}</span>
                    <span className="text-xs text-text-muted">{m.type}</span>
                    <span className="text-xs font-mono text-text-muted">{m.version}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color}`}>{cfg.label}</span>
                  </div>
                  <p className="text-xs text-text-muted mb-3">{m.desc}</p>
                  <div className="grid grid-cols-4 gap-3">
                    <div className="text-center"><span className="text-[10px] text-text-muted block">准确率</span><span className={`font-mono text-sm font-semibold ${m.accuracy > 0.9 ? 'text-up' : 'text-warning'}`}>{formatPercent(m.accuracy)}</span></div>
                    <div className="text-center"><span className="text-[10px] text-text-muted block">最近训练</span><span className="font-mono text-xs text-text-secondary">{m.lastTrain}</span></div>
                    <div className="text-center"><span className="text-[10px] text-text-muted block">7日调用</span><span className="font-mono text-sm text-text-primary">{m.calls7d}次</span></div>
                    <div className="text-center"><span className="text-[10px] text-text-muted block">版本</span><span className="font-mono text-xs text-text-secondary">{m.version}</span></div>
                  </div>
                </div>
              )
            })}
          </div>
        </CollapsibleSection>
      </motion.div>
    </div>
  )
}
