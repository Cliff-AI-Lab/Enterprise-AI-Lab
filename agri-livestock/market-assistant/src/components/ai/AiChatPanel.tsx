import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Bot, Send, Sparkles, User, Loader2 } from 'lucide-react'
import { defaultAiMessages, type CommodityDataSet } from '@/data/mockData'
import { chatCompletion } from '@/lib/iruidong'

interface Message { role: 'user' | 'assistant'; content: string; time: string }

interface Props {
  readonly commodityName: string
  readonly commodityData: CommodityDataSet
}

function getTimeStr(): string {
  const now = new Date()
  return `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}

export default function AiChatPanel({ commodityName, commodityData }: Props) {
  const cc = commodityData.coreConclusion
  const ps = commodityData.procurementSummary

  const systemPrompt = `你是一个专业的农牧行业行情分析智能助手，专注于企业采购决策支持。
当前分析品种：${commodityName}
- 现货价：${cc.currentPrice}元/吨
- 明日预测价：${cc.predictedPrice}元/吨
- 看涨概率：${Math.round(cc.trendAssessment.value * 100)}%
- 价格区间：${cc.priceRange.lower}-${cc.priceRange.upper}元/吨
- 采购建议：${ps.action}，理想采购价≤${ps.idealBuyBelow}元/吨
主要驱动因子：${commodityData.driverFactors.map((f, i) => `${i + 1}.${f.name}(${f.change})`).join(' ')}
请基于以上数据回答采购策略、行情走势等问题。简洁专业，200字以内。`

  const [messages, setMessages] = useState<Message[]>(defaultAiMessages.map(m => ({ ...m, role: m.role as 'assistant' })))
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { scrollRef.current && (scrollRef.current.scrollTop = scrollRef.current.scrollHeight) }, [messages])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    const userMsg: Message = { role: 'user', content: text, time: getTimeStr() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)
    try {
      const history = [...messages, userMsg].map(m => ({ role: m.role as 'system' | 'user' | 'assistant', content: m.content }))
      const reply = await chatCompletion([{ role: 'system', content: systemPrompt }, ...history], { temperature: 0.7, maxTokens: 500 })
      setMessages(prev => [...prev, { role: 'assistant', content: reply, time: getTimeStr() }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `[连接失败] ${err instanceof Error ? err.message : '请检查API配置'}`, time: getTimeStr() }])
    } finally { setLoading(false) }
  }

  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.6 }} className="card-base p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={16} className="text-neon" />
        <span className="text-xs font-medium text-text-secondary uppercase tracking-widest">AI 分析助手</span>
        <span className="text-[10px] text-text-muted font-mono ml-auto">睿动平台 · {commodityName}</span>
      </div>
      <div ref={scrollRef} className="space-y-3 max-h-[180px] overflow-y-auto mb-3">
        {messages.map((msg, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i < 2 ? 0.7 + i * 0.15 : 0 }} className={`flex gap-2.5 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-6 h-6 rounded flex items-center justify-center shrink-0 mt-0.5 ${msg.role === 'user' ? 'bg-forecast/10' : 'bg-neon/10'}`}>
              {msg.role === 'user' ? <User size={12} className="text-forecast" /> : <Bot size={12} className="text-neon" />}
            </div>
            <div className={`flex-1 min-w-0 ${msg.role === 'user' ? 'text-right' : ''}`}>
              <p className={`text-xs leading-relaxed ${msg.role === 'user' ? 'text-text-primary' : 'text-text-secondary'}`}>{msg.content}</p>
              <span className="text-[10px] text-text-muted font-mono mt-1 block">{msg.time}</span>
            </div>
          </motion.div>
        ))}
        {loading && <div className="flex gap-2.5"><div className="w-6 h-6 rounded bg-neon/10 flex items-center justify-center shrink-0"><Loader2 size={12} className="text-neon animate-spin" /></div><span className="text-xs text-text-muted">正在分析...</span></div>}
      </div>
      <div className="flex gap-2">
        <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()} placeholder={`关于${commodityName}的采购问题...`} disabled={loading} className="flex-1 bg-bg-elevated border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-neon/50 transition-colors disabled:opacity-50" />
        <button onClick={handleSend} disabled={loading || !input.trim()} className="px-3 py-2 rounded-lg bg-neon text-text-inverse hover:brightness-110 transition-all disabled:opacity-30"><Send size={14} /></button>
      </div>
    </motion.div>
  )
}
