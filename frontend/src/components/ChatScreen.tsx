import { useState, useRef, useEffect } from 'react'
import { Send, LogOut } from 'lucide-react'
import type { Message, Session } from '../types'
import { sendMessage, endSession } from '../api'
import { MessageBubble } from './MessageBubble'
import { TypingIndicator } from './TypingIndicator'
import { SafetyBanner } from './SafetyBanner'

interface Props {
  session: Session
  onSessionEnd: () => void
}

const WELCOME: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello, I'm here to listen and support you. How are you feeling today? You can share as much or as little as you'd like.",
  timestamp: new Date(),
}

export function ChatScreen({ session, onSessionEnd }: Props) {
  const [messages, setMessages] = useState<Message[]>([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [safetyTriggered, setSafetyTriggered] = useState(false)
  const [ended, setEnded] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading || ended) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    // Reset textarea height
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    try {
      const res = await sendMessage(session.session_id, text)
      if (res.safety_triggered) setSafetyTriggered(true)

      const assistantMsg: Message = {
        id: res.message_id ?? crypto.randomUUID(),
        role: 'assistant',
        content: res.response,
        timestamp: new Date(),
        meta: {
          safety_triggered: res.safety_triggered,
          framework_used: res.framework_used,
          emotions_detected: res.emotions_detected,
          themes_detected: res.themes_detected,
          sources: res.sources,
        },
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch {
      setMessages(prev => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: "I'm sorry, something went wrong. Please try again.",
          timestamp: new Date(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  const handleEnd = async () => {
    setEnded(true)
    await endSession(session.session_id)
    setMessages(prev => [
      ...prev,
      {
        id: 'end',
        role: 'assistant',
        content: "This session has ended. Take care of yourself, and don't hesitate to reach out again whenever you need support.",
        timestamp: new Date(),
      },
    ])
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-100 px-4 py-3 flex items-center gap-3 flex-shrink-0">
        <div className="w-8 h-8 bg-teal-500 rounded-full flex items-center justify-center text-white text-xs font-semibold">
          MS
        </div>
        <div className="flex-1">
          <p className="text-sm font-medium text-slate-800">Mindful Support</p>
          <p className="text-xs text-slate-400">Research-backed emotional support</p>
        </div>
        {!ended && (
          <button
            onClick={handleEnd}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors px-2 py-1.5 rounded-lg hover:bg-slate-50"
          >
            <LogOut className="w-3.5 h-3.5" />
            End session
          </button>
        )}
      </div>

      {/* Safety banner */}
      {safetyTriggered && <SafetyBanner />}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      {!ended ? (
        <div className="bg-white border-t border-slate-100 px-4 py-3 flex-shrink-0">
          <div className="flex items-end gap-2 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-2 focus-within:border-teal-400 focus-within:ring-2 focus-within:ring-teal-100 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              placeholder="Share what's on your mind…"
              rows={1}
              disabled={loading}
              className="flex-1 bg-transparent resize-none text-sm text-slate-700 placeholder-slate-400 outline-none py-1 max-h-40"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="w-8 h-8 bg-teal-600 hover:bg-teal-700 disabled:bg-slate-200 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors mb-0.5"
            >
              <Send className="w-3.5 h-3.5 text-white disabled:text-slate-400" />
            </button>
          </div>
          <p className="text-xs text-slate-300 text-center mt-2">
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>
      ) : (
        <div className="bg-white border-t border-slate-100 px-4 py-4 text-center flex-shrink-0">
          <button
            onClick={onSessionEnd}
            className="text-sm text-teal-600 hover:text-teal-700 font-medium"
          >
            Start a new session
          </button>
        </div>
      )}
    </div>
  )
}
