import { TriangleAlert, X } from 'lucide-react'
import { useState } from 'react'

export function SafetyBanner() {
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null

  return (
    <div className="bg-red-50 border-b border-red-200 px-4 py-3 flex items-start gap-3">
      <TriangleAlert className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-red-800">Crisis support detected</p>
        <p className="text-sm text-red-700 mt-0.5">
          If you're in immediate danger, please call emergency services (911) or a crisis line such as{' '}
          <strong>988 Suicide & Crisis Lifeline</strong> (call or text 988 in the US).
        </p>
      </div>
      <button onClick={() => setDismissed(true)} className="text-red-400 hover:text-red-600 flex-shrink-0">
        <X className="w-4 h-4" />
      </button>
    </div>
  )
}
