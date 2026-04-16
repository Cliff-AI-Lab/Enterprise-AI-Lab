import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

interface Props {
  readonly title: string
  readonly icon?: ReactNode
  readonly badge?: ReactNode
  readonly defaultOpen?: boolean
  readonly children: ReactNode
}

export default function CollapsibleSection({ title, icon, badge, defaultOpen = false, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="border border-border-default rounded-xl overflow-hidden bg-bg-card mb-4">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 hover:bg-bg-hover transition-colors"
      >
        <motion.div animate={{ rotate: open ? 90 : 0 }} transition={{ duration: 0.2 }}>
          <ChevronRight size={16} className="text-text-muted" />
        </motion.div>
        {icon && <span className="text-text-muted">{icon}</span>}
        <span className="text-sm font-display font-semibold text-text-primary">{title}</span>
        {badge && <span className="ml-auto">{badge}</span>}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-1 border-t border-border-default">
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
