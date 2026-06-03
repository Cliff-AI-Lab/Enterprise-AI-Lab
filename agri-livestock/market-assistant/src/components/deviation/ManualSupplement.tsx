import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Send, Star } from 'lucide-react'

interface ManualSupplementProps {
  readonly deviationId: string | null
  readonly onClose: () => void
}

const categories = ['政策变动', '突发事件', '行业内幕', '季节性偏差', '数据源异常', '其他']

export default function ManualSupplement({ deviationId, onClose }: ManualSupplementProps) {
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [direction, setDirection] = useState<'up' | 'down'>('up')
  const [magnitude, setMagnitude] = useState('')
  const [duration, setDuration] = useState('')
  const [credibility, setCredibility] = useState(3)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = () => {
    setSubmitted(true)
    setTimeout(() => {
      setSubmitted(false)
      onClose()
    }, 1500)
  }

  return (
    <AnimatePresence>
      {deviationId && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
          onClick={(e) => e.target === e.currentTarget && onClose()}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-lg card-base border-border-accent p-6"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="font-display text-base font-bold text-text-primary">人工补录信息</h3>
                <p className="text-xs text-text-muted font-mono mt-0.5">{deviationId}</p>
              </div>
              <button onClick={onClose} className="p-1 rounded hover:bg-bg-hover text-text-muted">
                <X size={16} />
              </button>
            </div>

            {submitted ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="py-12 flex flex-col items-center gap-3"
              >
                <div className="w-12 h-12 rounded-full bg-up/10 flex items-center justify-center">
                  <Send size={20} className="text-up" />
                </div>
                <p className="text-sm text-text-primary font-medium">提交成功</p>
                <p className="text-xs text-text-muted">信息将用于模型优化</p>
              </motion.div>
            ) : (
              <div className="space-y-4">
                {/* Category */}
                <div>
                  <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                    原因分类
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {categories.map((c) => (
                      <button
                        key={c}
                        onClick={() => setCategory(c)}
                        className={`px-3 py-1.5 rounded text-xs transition-all ${
                          category === c
                            ? 'bg-neon text-text-inverse font-medium'
                            : 'bg-bg-elevated text-text-secondary hover:text-text-primary border border-border-default hover:border-border-strong'
                        }`}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Description */}
                <div>
                  <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                    补充说明
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="请描述导致偏差的原因、影响范围及可能的持续时间..."
                    rows={3}
                    className="w-full bg-bg-elevated border border-border-default rounded-lg px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-neon/50 transition-colors resize-none"
                  />
                </div>

                {/* Direction & Magnitude */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                      影响方向
                    </label>
                    <div className="flex rounded border border-border-default overflow-hidden">
                      <button
                        onClick={() => setDirection('up')}
                        className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
                          direction === 'up' ? 'bg-up/20 text-up' : 'bg-bg-elevated text-text-muted'
                        }`}
                      >
                        ↑ 上行
                      </button>
                      <button
                        onClick={() => setDirection('down')}
                        className={`flex-1 py-1.5 text-xs font-medium transition-colors ${
                          direction === 'down' ? 'bg-down/20 text-down' : 'bg-bg-elevated text-text-muted'
                        }`}
                      >
                        ↓ 下行
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                      幅度 (元/吨)
                    </label>
                    <input
                      type="number"
                      value={magnitude}
                      onChange={(e) => setMagnitude(e.target.value)}
                      placeholder="150"
                      className="w-full bg-bg-elevated border border-border-default rounded px-3 py-1.5 text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-neon/50 transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                      持续 (天)
                    </label>
                    <input
                      type="number"
                      value={duration}
                      onChange={(e) => setDuration(e.target.value)}
                      placeholder="14"
                      className="w-full bg-bg-elevated border border-border-default rounded px-3 py-1.5 text-sm font-mono text-text-primary placeholder:text-text-muted focus:outline-none focus:border-neon/50 transition-colors"
                    />
                  </div>
                </div>

                {/* Credibility */}
                <div>
                  <label className="block text-xs text-text-secondary mb-2 uppercase tracking-widest">
                    可信度评级
                  </label>
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((v) => (
                      <button
                        key={v}
                        onClick={() => setCredibility(v)}
                        className="p-0.5"
                      >
                        <Star
                          size={20}
                          className={`transition-colors ${
                            v <= credibility ? 'text-neon fill-neon' : 'text-text-muted'
                          }`}
                        />
                      </button>
                    ))}
                    <span className="ml-2 text-xs text-text-muted self-center">
                      {credibility}/5
                    </span>
                  </div>
                </div>

                {/* Submit */}
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={handleSubmit}
                    disabled={!category || !description}
                    className="flex-1 py-2.5 rounded-lg bg-neon text-text-inverse text-sm font-semibold hover:brightness-110 transition-all disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    <Send size={14} />
                    确认提交
                  </button>
                  <button
                    onClick={onClose}
                    className="px-4 py-2.5 rounded-lg border border-border-default text-sm text-text-secondary hover:text-text-primary hover:border-border-strong transition-colors"
                  >
                    取消
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
