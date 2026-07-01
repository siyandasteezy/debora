import { useState } from 'react'
import { Heart } from 'lucide-react'

interface Props {
  onStart: (anonymousId: string, consent: boolean) => void
  loading: boolean
}

export function ConsentScreen({ onStart, loading }: Props) {
  const [consent, setConsent] = useState(false)

  const handleStart = () => {
    const id = `anon_${Math.random().toString(36).slice(2, 11)}`
    onStart(id, consent)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 max-w-md w-full p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 bg-teal-50 rounded-xl flex items-center justify-center">
            <Heart className="w-5 h-5 text-teal-600" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800 leading-tight">Mindful Support</h1>
            <p className="text-xs text-slate-400">Mental Health Reasoning Engine</p>
          </div>
        </div>

        <p className="text-slate-600 text-sm leading-relaxed mb-4">
          This is a research-backed emotional support tool offering psychoeducation and coping guidance. It is <strong className="text-slate-700">not a substitute</strong> for professional mental health care.
        </p>

        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 mb-6 text-sm text-amber-800">
          If you are in crisis or need immediate help, please contact a crisis line or emergency services in your area.
        </div>

        <label className="flex items-start gap-3 cursor-pointer mb-6 group">
          <div className="relative mt-0.5 flex-shrink-0">
            <input
              type="checkbox"
              className="sr-only"
              checked={consent}
              onChange={e => setConsent(e.target.checked)}
            />
            <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${consent ? 'bg-teal-500 border-teal-500' : 'border-slate-300 group-hover:border-teal-400'}`}>
              {consent && (
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>
          </div>
          <span className="text-sm text-slate-600">
            I understand this tool is for support only and I consent to anonymous session data being used to improve responses.
          </span>
        </label>

        <button
          onClick={handleStart}
          disabled={loading}
          className="w-full bg-teal-600 hover:bg-teal-700 disabled:bg-teal-300 text-white font-medium py-3 rounded-xl transition-colors text-sm"
        >
          {loading ? 'Starting session…' : 'Begin session'}
        </button>
      </div>
    </div>
  )
}
