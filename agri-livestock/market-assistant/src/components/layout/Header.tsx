import { motion } from 'framer-motion'
import { Activity, Building2, User, Bell, Sun, Moon } from 'lucide-react'
import { useApp } from '@/context/AppContext'

export default function Header() {
  const { theme, toggleTheme } = useApp()

  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center justify-between px-5 py-2.5 border-b border-border-default bg-bg-card"
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-neon flex items-center justify-center">
          <Activity size={16} className="text-text-inverse" />
        </div>
        <div>
          <h1 className="font-display text-sm font-bold tracking-tight text-text-primary">
            行情分析智能助手
          </h1>
          <p className="text-[10px] text-text-muted font-mono">企业采购决策平台</p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <span className="w-1.5 h-1.5 rounded-full bg-up animate-pulse" />
          系统运行中
        </div>

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg hover:bg-bg-hover transition-colors"
          title={theme === 'dark' ? '切换为亮色' : '切换为暗色'}
        >
          {theme === 'dark'
            ? <Sun size={16} className="text-text-secondary hover:text-warning transition-colors" />
            : <Moon size={16} className="text-text-secondary hover:text-info transition-colors" />}
        </button>

        <button className="relative p-2 rounded-lg hover:bg-bg-hover transition-colors">
          <Bell size={16} className="text-text-muted" />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-down" />
        </button>

        <div className="flex items-center gap-2 pl-3 border-l border-border-default">
          <Building2 size={14} className="text-text-muted" />
          <span className="text-xs text-text-secondary">软通动力</span>
          <div className="w-7 h-7 rounded-full bg-bg-elevated flex items-center justify-center">
            <User size={13} className="text-text-muted" />
          </div>
        </div>
      </div>
    </motion.header>
  )
}
