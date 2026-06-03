import { motion } from 'framer-motion'
import { LayoutDashboard, Database, Brain, Bot, Link2, BarChart3 } from 'lucide-react'
import { useApp, type PageId } from '@/context/AppContext'

const NAV_ITEMS: { id: PageId; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'overview', label: '总览仪表盘', icon: LayoutDashboard },
  { id: 'data', label: '数据管理', icon: Database },
  { id: 'model', label: '模型管理', icon: Brain },
  { id: 'agent', label: '智能体管理', icon: Bot },
  { id: 'integration', label: '应用对接', icon: Link2 },
  { id: 'analysis', label: '行情分析', icon: BarChart3 },
]

export default function Sidebar() {
  const { page, setPage } = useApp()

  return (
    <motion.aside
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="w-52 shrink-0 border-r border-border-default bg-bg-card flex flex-col"
    >
      <nav className="flex-1 py-4 px-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const active = page === item.id
          return (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all ${
                active
                  ? 'bg-neon/10 text-neon font-medium'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-hover'
              }`}
            >
              <Icon size={16} className={active ? 'text-neon' : 'text-text-muted'} />
              {item.label}
              {active && (
                <motion.div layoutId="nav-dot" className="ml-auto w-1.5 h-1.5 rounded-full bg-neon" />
              )}
            </button>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border-default">
        <div className="text-[10px] text-text-muted font-mono leading-relaxed">
          <div>行情分析智能助手 v3.0</div>
          <div>企业采购决策平台</div>
        </div>
      </div>
    </motion.aside>
  )
}
