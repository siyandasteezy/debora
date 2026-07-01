import { useState } from 'react'
import { BookOpen, ChevronDown, ChevronUp } from 'lucide-react'
import type { Message } from '../types'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const isUser = message.role === 'user'
  const meta = message.meta

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? 'bg-teal-600 text-white rounded-tr-sm'
            : 'bg-white border border-slate-100 text-slate-700 rounded-tl-sm shadow-xs'
        }`}
      >
        {message.content}
      </div>

      {meta && (
        <div className="max-w-[80%] w-full space-y-1.5">
          {(meta.emotions_detected.length > 0 || meta.themes_detected.length > 0) && (
            <div className="flex flex-wrap gap-1.5 px-1">
              {meta.emotions_detected.map(e => (
                <span key={e} className="text-xs bg-violet-50 text-violet-600 border border-violet-100 rounded-full px-2 py-0.5">
                  {e}
                </span>
              ))}
              {meta.themes_detected.map(t => (
                <span key={t} className="text-xs bg-blue-50 text-blue-600 border border-blue-100 rounded-full px-2 py-0.5">
                  {t}
                </span>
              ))}
            </div>
          )}

          {meta.framework_used && (
            <p className="text-xs text-slate-400 px-1">
              Framework: <span className="text-slate-500">{meta.framework_used}</span>
            </p>
          )}

          {meta.sources.length > 0 && (
            <div className="border border-slate-100 rounded-xl overflow-hidden bg-white">
              <button
                onClick={() => setSourcesOpen(v => !v)}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-500 hover:bg-slate-50 transition-colors"
              >
                <BookOpen className="w-3.5 h-3.5" />
                <span>{meta.sources.length} source{meta.sources.length !== 1 ? 's' : ''}</span>
                <span className="ml-auto">
                  {sourcesOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </span>
              </button>
              {sourcesOpen && (
                <div className="border-t border-slate-100 divide-y divide-slate-50">
                  {meta.sources.map(src => (
                    <div key={src.id} className="px-3 py-2">
                      <p className="text-xs font-medium text-slate-700">{src.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">{src.citation}{src.year ? ` (${src.year})` : ''}</p>
                      {src.url && (
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-xs text-teal-600 hover:underline mt-0.5 block">
                          View source
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-slate-300 px-1">
        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </p>
    </div>
  )
}
