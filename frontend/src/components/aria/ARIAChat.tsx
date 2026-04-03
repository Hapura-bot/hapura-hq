import { useState, useRef, useEffect } from 'react'
import { Bot, X, Send, Loader2, Minimize2 } from 'lucide-react'
import { api } from '../../api/client'
import { motion, AnimatePresence } from 'framer-motion'

interface Message {
  role: 'user' | 'assistant'
  content: string
  ts: number
}

interface ConversationEntry {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

export default function ARIAChat() {
  const [open, setOpen]       = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput]     = useState('')
  const [loading, setLoading] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Load conversation history on first open
  useEffect(() => {
    if (!open || historyLoaded) return
    api.get<ConversationEntry[]>('/agents/hq_assistant/conversations')
      .then(data => {
        setMessages(data.map(d => ({
          role: d.role,
          content: d.content,
          ts: new Date(d.timestamp).getTime(),
        })))
        setHistoryLoaded(true)
      })
      .catch(() => setHistoryLoaded(true))
  }, [open, historyLoaded])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  async function send() {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = { role: 'user', content: text, ts: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const { reply } = await api.post<{ reply: string }>('/agents/hq_assistant/chat', { message: text })
      setMessages(prev => [...prev, { role: 'assistant', content: reply, ts: Date.now() }])
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Lỗi kết nối'
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ ${msg}`, ts: Date.now() }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full bg-brand/20 border border-brand/50 flex items-center justify-center hover:bg-brand/30 hover:glow-brand transition-all shadow-lg"
        title="Chat với ARIA"
      >
        <Bot size={20} className="text-brand" />
      </button>

      {/* Chat panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="fixed bottom-22 right-6 z-50 w-80 sm:w-96 h-[520px] flex flex-col bg-dark-800 border border-dark-500 rounded-xl shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-dark-600 bg-dark-900">
              <div className="flex items-center gap-2">
                <Bot size={16} className="text-brand" />
                <span className="text-brand font-game font-bold tracking-widest text-sm">ARIA</span>
                <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
              </div>
              <div className="flex items-center gap-1">
                <button onClick={() => setOpen(false)} className="p-1 text-slate-500 hover:text-slate-300 transition-colors">
                  <Minimize2 size={14} />
                </button>
                <button onClick={() => setOpen(false)} className="p-1 text-slate-500 hover:text-neon-red transition-colors">
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin">
              {messages.length === 0 && !loading && (
                <div className="text-center text-slate-600 text-xs font-mono mt-8 space-y-1">
                  <Bot size={28} className="mx-auto text-brand/30 mb-3" />
                  <p>Xin chào Anh Victor!</p>
                  <p>Em là ARIA, trợ lý của Hapura HQ.</p>
                  <p className="text-slate-700">Hỏi em bất cứ điều gì về 4 dự án nhé.</p>
                </div>
              )}

              {messages.map((m, i) => (
                <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div
                    className={`max-w-[85%] px-3 py-2 rounded-lg text-xs leading-relaxed whitespace-pre-wrap ${
                      m.role === 'user'
                        ? 'bg-brand/20 border border-brand/30 text-slate-200'
                        : 'bg-dark-700 border border-dark-500 text-slate-300'
                    }`}
                  >
                    {m.role === 'assistant' && (
                      <span className="text-brand font-bold text-[10px] tracking-widest block mb-1">ARIA</span>
                    )}
                    {m.content}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start">
                  <div className="bg-dark-700 border border-dark-500 px-3 py-2 rounded-lg">
                    <Loader2 size={14} className="text-brand animate-spin" />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="p-3 border-t border-dark-600">
              <div className="flex items-end gap-2">
                <textarea
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKey}
                  placeholder="Hỏi ARIA..."
                  rows={1}
                  className="flex-1 bg-dark-900 border border-dark-500 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-600 resize-none focus:outline-none focus:border-brand/50 transition-colors"
                  style={{ maxHeight: '80px' }}
                />
                <button
                  onClick={send}
                  disabled={!input.trim() || loading}
                  className="p-2 bg-brand/20 border border-brand/40 rounded-lg text-brand hover:bg-brand/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                >
                  <Send size={14} />
                </button>
              </div>
              <p className="text-slate-700 text-[10px] mt-1 font-mono">Enter để gửi · Shift+Enter xuống dòng</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
