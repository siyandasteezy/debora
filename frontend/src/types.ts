export interface Session {
  session_id: string
  user_id: string
  status: string
  consent_given: boolean
}

export interface SourceCitation {
  id: string
  title: string
  source_type: string
  citation: string
  year: number | null
  url: string | null
  evidence_level: string | null
  similarity_score: number
}

export interface ChatResponse {
  response: string
  session_id: string
  safety_triggered: boolean
  framework_used: string
  emotions_detected: string[]
  themes_detected: string[]
  sources: SourceCitation[]
  message_id: string | null
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  meta?: {
    safety_triggered: boolean
    framework_used: string
    emotions_detected: string[]
    themes_detected: string[]
    sources: SourceCitation[]
  }
}
