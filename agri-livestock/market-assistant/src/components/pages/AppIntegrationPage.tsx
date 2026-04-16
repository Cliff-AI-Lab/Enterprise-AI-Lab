import { motion } from 'framer-motion'
import { Link2, Warehouse, ShoppingCart, Server, CheckCircle2, XCircle, Clock, ArrowRightLeft, Settings } from 'lucide-react'
import CollapsibleSection from '@/components/shared/CollapsibleSection'
import { getInventoryData } from '@/data/mockData'
import { formatPrice } from '@/lib/utils'

const syncRecords = [
  { time: '09:30', type: '库存同步', direction: '← 拉取', detail: '5个品种库存数据已更新', status: 'ok' },
  { time: '09:31', type: '采购单推送', direction: '→ 推送', detail: '豆粕采购建议500吨已推送至采购系统', status: 'ok' },
  { time: '08:00', type: '库存同步', direction: '← 拉取', detail: '5个品种库存数据已更新', status: 'ok' },
  { time: '07:32', type: '预警推送', direction: '→ 推送', detail: '鱼粉库存预警已发送至ERP', status: 'ok' },
]

export default function AppIntegrationPage() {
  const inventory = getInventoryData()

  return (
    <div className="flex-1 p-4 overflow-y-auto ">
      <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
        <h2 className="font-display text-xl font-bold text-text-primary mb-1">应用对接</h2>
        <p className="text-xs text-text-muted mb-6">库存系统、采购系统、ERP 集成管理</p>

        <CollapsibleSection title="库存系统对接" icon={<Warehouse size={14} />}
          badge={<span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up flex items-center gap-1"><CheckCircle2 size={10} />已连接</span>} defaultOpen>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-3 rounded bg-bg-elevated">
              <h4 className="text-xs text-text-muted mb-2">连接配置</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-text-muted">API地址</span><span className="font-mono text-xs text-text-secondary">https://erp.internal/api/inventory</span></div>
                <div className="flex justify-between"><span className="text-text-muted">同步频率</span><span className="text-text-primary">每小时</span></div>
                <div className="flex justify-between"><span className="text-text-muted">最近同步</span><span className="text-text-primary">09:30 (成功)</span></div>
                <div className="flex justify-between"><span className="text-text-muted">对接品种</span><span className="text-text-primary">5个</span></div>
              </div>
            </div>
            <div className="p-3 rounded bg-bg-elevated">
              <h4 className="text-xs text-text-muted mb-2">当前库存概览</h4>
              <div className="space-y-1.5">
                {inventory.map(item => (
                  <div key={item.commodityId} className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{item.commodityName}</span>
                    <span className="font-mono text-text-primary">{formatPrice(item.currentStock)}吨</span>
                    <span className={`text-xs ${item.status === 'danger' ? 'text-down' : item.status === 'warning' ? 'text-warning' : 'text-up'}`}>{item.currentDays}天</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="采购系统对接" icon={<ShoppingCart size={14} />}
          badge={<span className="text-xs px-1.5 py-0.5 rounded bg-up/10 text-up flex items-center gap-1"><CheckCircle2 size={10} />已连接</span>}>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="p-3 rounded bg-bg-elevated">
              <h4 className="text-xs text-text-muted mb-2">连接配置</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-text-muted">API地址</span><span className="font-mono text-xs text-text-secondary">https://scm.internal/api/purchase</span></div>
                <div className="flex justify-between"><span className="text-text-muted">推送模式</span><span className="text-text-primary">审批后推送</span></div>
                <div className="flex justify-between"><span className="text-text-muted">最近推送</span><span className="text-text-primary">09:31 (成功)</span></div>
              </div>
            </div>
            <div className="p-3 rounded bg-bg-elevated">
              <h4 className="text-xs text-text-muted mb-2">推送配置</h4>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">自动推送采购建议</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-neon/10 text-neon">已开启</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">库存预警自动触发</span>
                  <span className="text-xs px-2 py-0.5 rounded bg-neon/10 text-neon">已开启</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-text-muted">审批流程</span>
                  <span className="text-text-primary">需采购经理确认</span>
                </div>
              </div>
            </div>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="ERP & 其他系统" icon={<Server size={14} />}
          badge={<span className="text-xs px-1.5 py-0.5 rounded bg-warning/10 text-warning flex items-center gap-1"><Clock size={10} />部分对接</span>}>
          <div className="space-y-2 mb-4">
            <div className="p-3 rounded bg-bg-elevated flex items-center gap-3">
              <CheckCircle2 size={14} className="text-up" />
              <span className="text-sm text-text-primary w-32">ERP系统</span>
              <span className="text-xs font-mono text-text-muted flex-1">https://erp.internal.corp</span>
              <span className="text-xs text-up">已对接</span>
            </div>
            <div className="p-3 rounded bg-bg-elevated flex items-center gap-3">
              <Clock size={14} className="text-warning" />
              <span className="text-sm text-text-primary w-32">OA审批系统</span>
              <span className="text-xs font-mono text-text-muted flex-1">https://oa.internal.corp</span>
              <span className="text-xs text-warning">对接中</span>
            </div>
            <div className="p-3 rounded bg-bg-elevated flex items-center gap-3">
              <XCircle size={14} className="text-text-muted" />
              <span className="text-sm text-text-secondary w-32">钉钉通知</span>
              <span className="text-xs font-mono text-text-muted flex-1">Webhook</span>
              <span className="text-xs text-text-muted">未配置</span>
              <button className="text-xs px-2 py-0.5 rounded border border-border-default text-text-muted hover:text-neon hover:border-neon/50"><Settings size={10} className="inline mr-1" />配置</button>
            </div>
          </div>
        </CollapsibleSection>

        <CollapsibleSection title="同步记录" icon={<ArrowRightLeft size={14} />} badge={<span className="text-xs text-text-muted">今日 {syncRecords.length} 次</span>}>
          <div className="space-y-1.5">
            {syncRecords.map((r, i) => (
              <div key={i} className="flex items-center gap-3 p-2.5 rounded bg-bg-elevated text-xs">
                <span className="font-mono text-text-muted w-10">{r.time}</span>
                <CheckCircle2 size={10} className="text-up" />
                <span className="text-text-secondary w-24">{r.type}</span>
                <span className="text-text-muted w-16">{r.direction}</span>
                <span className="text-text-secondary flex-1">{r.detail}</span>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      </motion.div>
    </div>
  )
}
