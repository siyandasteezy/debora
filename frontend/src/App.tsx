import { useState } from 'react'
import './index.css'
import type { Session } from './types'
import { createSession } from './api'
import { ConsentScreen } from './components/ConsentScreen'
import { ChatScreen } from './components/ChatScreen'

export default function App() {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleStart = async (anonymousId: string, consent: boolean) => {
    setLoading(true)
    setError(null)
    try {
      const s = await createSession(anonymousId, consent)
      setSession(s)
    } catch {
      setError('Could not connect to the server. Please make sure the API is running.')
    } finally {
      setLoading(false)
    }
  }

  const handleSessionEnd = () => setSession(null)

  if (session) {
    return <ChatScreen session={session} onSessionEnd={handleSessionEnd} />
  }

  return (
    <>
      <ConsentScreen onStart={handleStart} loading={loading} />
      {error && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-red-600 text-white text-sm px-4 py-2 rounded-xl shadow-lg">
          {error}
        </div>
      )}
    </>
  )
}
