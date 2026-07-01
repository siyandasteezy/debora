import type { Session, ChatResponse } from './types'

const API_URL = import.meta.env.VITE_API_URL ?? ''
const BASE = `${API_URL}/api/v1`

export async function createSession(anonymousId: string, consentGiven: boolean): Promise<Session> {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ anonymous_id: anonymousId, consent_given: consentGiven }),
  })
  if (!res.ok) throw new Error('Failed to create session')
  return res.json()
}

export async function sendMessage(
  sessionId: string,
  message: string,
): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) throw new Error('Failed to send message')
  return res.json()
}

export async function endSession(sessionId: string): Promise<void> {
  await fetch(`${BASE}/sessions/${sessionId}`, { method: 'DELETE' })
}
